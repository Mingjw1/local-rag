"""Qdrant 向量数据库客户端 — 支持混合搜索（密集向量 + 关键词检索）"""

import math
import re
from typing import List, Optional

from qdrant_client import QdrantClient as QdrantSyncClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams

from app.core.config import settings


HYBRID_DENSE_WEIGHT = 0.7
HYBRID_SPARSE_WEIGHT = 0.3
RRF_K = 60  # Reciprocal Rank Fusion 常数


class QdrantClient:
    """Qdrant 向量数据库封装"""

    def __init__(self):
        self.client = QdrantSyncClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            api_key=settings.qdrant_api_key or None,
            timeout=30,
        )

    async def ensure_collection(self, collection_name: str, vector_size: int):
        """确保 collection 存在，不存在则创建（含全文索引）"""
        collections = self.client.get_collections().collections
        exists = any(c.name == collection_name for c in collections)

        if not exists:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE,
                ),
                optimizers_config=models.OptimizersConfigDiff(
                    default_segment_number=2,
                    indexing_threshold=20000,
                ),
                hnsw_config=models.HnswConfigDiff(
                    m=16,
                    ef_construct=100,
                    full_scan_threshold=10000,
                ),
            )

        # 确保 content 字段有全文索引（用于 BM25 风格搜索）
        try:
            self.client.create_payload_index(
                collection_name=collection_name,
                field_name="content",
                field_schema=models.TextIndexParams(
                    type=models.TextIndexType.TEXT,
                    tokenizer=models.TokenizerType.WORD,
                    min_token_len=1,
                    max_token_len=100,
                ),
            )
        except Exception:
            pass  # 索引已存在

        # metadata 字段索引（用于过滤）
        for field in ["kb_id"]:
            try:
                self.client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field,
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
            except Exception:
                pass

    async def upsert_points(self, collection_name: str, points: List[dict]):
        """批量写入向量点"""
        self.client.upsert(
            collection_name=collection_name,
            points=[
                models.PointStruct(
                    id=p["id"],
                    vector=p["vector"],
                    payload=p.get("payload", {}),
                )
                for p in points
            ],
        )

    async def search_points(
        self,
        collection_name: str,
        vector: List[float],
        limit: int = 20,
        score_threshold: Optional[float] = None,
        query_filter: Optional[dict] = None,
        hybrid: bool = False,
        query_text: Optional[str] = None,
    ) -> List[models.ScoredPoint]:
        """搜索相似向量

        Args:
            hybrid: 是否启用混合搜索（密集向量 + 全文检索）
            query_text: 关键词查询（hybrid=True 时必填）
        """
        qdrant_filter = None
        if query_filter:
            qdrant_filter = models.Filter(**query_filter)

        if hybrid and query_text:
            return await self._hybrid_search(
                collection_name=collection_name,
                vector=vector,
                query_text=query_text,
                limit=limit,
                query_filter=qdrant_filter,
            )

        # 纯向量搜索
        resp = self.client.query_points(
            collection_name=collection_name,
            query=vector,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=qdrant_filter,
        )
        return resp.points

    def _tokenize_query(self, text: str) -> List[str]:
        """将查询分词为关键词 tokens"""
        # 提取中文/英文/数字 token
        tokens = []
        # 匹配中文字符序列
        tokens.extend(re.findall(r'[一-鿿]+', text))
        # 匹配英文单词（至少 2 个字母）
        tokens.extend(re.findall(r'[a-zA-Z]{2,}', text))
        return list(set(tokens))

    async def _keyword_search_points(
        self,
        collection_name: str,
        query_text: str,
        limit: int,
        query_filter: Optional[models.Filter] = None,
    ) -> List[models.ScoredPoint]:
        """关键词搜索：使用 scroll + MatchText 过滤"""
        tokens = self._tokenize_query(query_text)
        if not tokens:
            return []

        # 为每个 token 创建 MatchText 条件
        should_conditions = [
            models.FieldCondition(
                key="content",
                match=models.MatchText(text=token),
            )
            for token in tokens
        ]

        scroll_filter = models.Filter(
            must=query_filter.must if query_filter and query_filter.must else [],
            should=should_conditions,
        )

        resp = self.client.scroll(
            collection_name=collection_name,
            limit=limit,
            filter=scroll_filter,
            with_payload=True,
        )
        points = resp[0]

        # 计算每个点的关键词匹配得分
        scored = []
        for p in points:
            content = (p.payload or {}).get("content", "")
            match_count = sum(1 for t in tokens if t.lower() in content.lower())
            score = match_count / len(tokens) if tokens else 0
            p.score = round(score, 4)
            scored.append(p)

        scored.sort(key=lambda x: -x.score)
        return scored[:limit]

    async def _hybrid_search(
        self,
        collection_name: str,
        vector: List[float],
        query_text: str,
        limit: int,
        query_filter: Optional[models.Filter] = None,
    ) -> List[models.ScoredPoint]:
        """混合搜索：密集向量 + 关键词搜索 → RRF 合并"""
        if not query_text.strip():
            raise ValueError("query_text is required for hybrid search")

        dense_limit = max(limit * 2, 20)

        # 1. 密集向量搜索
        dense_resp = self.client.query_points(
            collection_name=collection_name,
            query=vector,
            limit=dense_limit,
            query_filter=query_filter,
        )
        dense_points = dense_resp.points

        # 2. 关键词搜索（scroll + MatchText）
        keyword_points = await self._keyword_search_points(
            collection_name=collection_name,
            query_text=query_text,
            limit=dense_limit,
            query_filter=query_filter,
        )

        # 3. RRF 合并
        all_ids = set()
        all_points = {}
        for p in dense_points:
            all_ids.add(p.id)
            if p.id not in all_points:
                all_points[p.id] = p
        for p in keyword_points:
            all_ids.add(p.id)
            if p.id not in all_points:
                all_points[p.id] = p

        def rrf_score(point_id) -> float:
            score = 0.0
            for rank, p in enumerate(sorted(dense_points, key=lambda x: -x.score)):
                if p.id == point_id:
                    score += HYBRID_DENSE_WEIGHT / (RRF_K + rank + 1)
                    break
            for rank, p in enumerate(sorted(keyword_points, key=lambda x: -x.score)):
                if p.id == point_id:
                    score += HYBRID_SPARSE_WEIGHT / (RRF_K + rank + 1)
                    break
            return score

        scored = sorted(
            [(pid, rrf_score(pid)) for pid in all_ids],
            key=lambda x: -x[1],
        )[:limit]

        results = []
        for pid, score in scored:
            point = all_points[pid]
            point.score = round(score, 4)
            results.append(point)

        return results

    async def delete_points(self, collection_name: str, point_ids: List[str]):
        """删除向量点"""
        self.client.delete(
            collection_name=collection_name,
            points_selector=models.PointIdsList(points=point_ids),
        )

    async def keyword_search(
        self,
        collection_name: str,
        query: str,
        limit: int = 20,
        query_filter: Optional[dict] = None,
    ) -> List[models.ScoredPoint]:
        """纯关键词搜索（使用 scroll + MatchText）"""
        qdrant_filter = None
        if query_filter:
            qdrant_filter = models.Filter(**query_filter)
        return await self._keyword_search_points(
            collection_name=collection_name,
            query_text=query,
            limit=limit,
            query_filter=qdrant_filter,
        )

    async def collection_info(self, collection_name: str) -> dict:
        """获取 collection 信息"""
        info = self.client.get_collection(collection_name)
        return {
            "name": collection_name,
            "points_count": info.points_count,
            "status": info.status,
            "vector_size": info.config.params.vectors.size,
            "optimizer_status": info.optimizer_status,
        }

    async def close(self):
        self.client.close()


# 全局单例
qdrant_client = QdrantClient()
