"""Qdrant 向量数据库客户端"""

from typing import List

from qdrant_client import QdrantClient as QdrantSyncClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams

from app.core.config import settings


class QdrantClient:
    """Qdrant 向量数据库封装"""

    def __init__(self):
        host = settings.qdrant_host
        port = settings.qdrant_port
        api_key = settings.qdrant_api_key

        self.client = QdrantSyncClient(
            host=host,
            port=port,
            api_key=api_key or None,
            timeout=30,
        )

    async def ensure_collection(self, collection_name: str, vector_size: int):
        """确保 collection 存在，不存在则创建"""
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
        score_threshold: float | None = None,
        query_filter: dict | None = None,
    ) -> List[models.ScoredPoint]:
        """搜索相似向量"""
        qdrant_filter = None
        if query_filter:
            qdrant_filter = models.Filter(**query_filter)

        resp = self.client.query_points(
            collection_name=collection_name,
            query=vector,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=qdrant_filter,
        )
        return resp.points

    async def delete_points(self, collection_name: str, point_ids: List[str]):
        """删除向量点"""
        self.client.delete(
            collection_name=collection_name,
            points_selector=models.PointIdsList(
                points=point_ids,
            ),
        )

    async def collection_info(self, collection_name: str) -> dict:
        """获取 collection 信息"""
        info = self.client.get_collection(collection_name)
        return {
            "name": collection_name,
            "points_count": info.points_count,
            "status": info.status,
            "vector_size": info.config.params.vectors.size,
        }

    async def close(self):
        self.client.close()


# 全局单例
qdrant_client = QdrantClient()
