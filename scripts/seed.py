#!/usr/bin/env python3
"""测试数据导入脚本 — 创建知识库并导入示例文档"""

import asyncio
import httpx
import sys

BASE_URL = "http://localhost:8000"

SAMPLE_DOCS = [
    {
        "title": "LLM Wiki 模式介绍",
        "content": """# LLM Wiki 模式

## 核心概念

LLM Wiki 是一种基于大语言模型的知识库构建模式。与传统的 RAG（检索增强生成）不同，
LLM Wiki 不仅从原始文档中检索信息，还会持续构建和维护一个结构化的知识库。

## 三层架构

1. **原始文档层**：不可变的源文件，包括文章、论文、报告等
2. **Wiki 层**：LLM 自动生成的 markdown 文件，包括摘要页面、概念页面、实体页面
3. **Schema 层**：配置文件，定义 Wiki 的结构和维护规则

## 三大操作

- **Ingest（导入）**：读取新文档 → 提取关键信息 → 整合到现有 Wiki
- **Query（查询）**：搜索 Wiki 页面 → 综合生成回答
- **Lint（检查）**：周期性健康检查 → 发现矛盾、孤儿页、断裂链接

## 优势

- 知识持续积累，而非每次都重新检索
- 交叉引用自动维护
- 矛盾自动标记
""",
    },
    {
        "title": "RAG 技术原理",
        "content": """# RAG 技术原理

## 什么是 RAG

RAG（Retrieval-Augmented Generation）是一种结合信息检索和文本生成的技术范式。

## 工作流程

1. **文档索引**：文档 → 分块 → Embedding → 存储到向量数据库
2. **检索**：用户查询 → Embedding → 向量相似度搜索 → Top-K 文档块
3. **生成**：查询 + 检索结果 → LLM → 生成回答

## 关键技术

- **Embedding 模型**：将文本转为向量，如 BGE、E5、nomic-embed-text
- **向量数据库**：高效存储和搜索向量，如 Qdrant、Milvus、Weaviate
- **重排序**：对检索结果进一步排序，提升精度
- **混合搜索**：结合向量搜索和关键词搜索（BM25）

## 本地部署优势

- 数据不出域，满足合规要求
- 无 API 调用成本
- 可定制检索策略和模型
""",
    },
    {
        "title": "Qdrant 向量数据库入门",
        "content": """# Qdrant 向量数据库

## 简介

Qdrant 是一个用 Rust 编写的高性能向量数据库，专为向量相似度搜索设计。

## 核心概念

- **Collection**：向量集合，类似关系数据库中的表
- **Point**：数据点，包含向量和 payload（元数据）
- **HNSW 索引**：分层可导航小世界图，高效近似最近邻搜索

## 关键特性

- 支持过滤搜索（基于 payload 的条件过滤）
- 支持余弦、内积、欧几里得距离
- 内置 BM25 文本搜索（混合搜索）
- 快照备份和恢复
- 分布式集群模式

## 部署方式

- 单节点：Docker 一键部署，适合 MVP
- 集群：多节点分片和复制，适合生产环境
""",
    },
]


async def main():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        # 1. 检查服务是否就绪
        try:
            resp = await client.get("/health")
            resp.raise_for_status()
            print("✓ 服务连接成功")
        except Exception as e:
            print(f"❌ 服务未就绪: {e}")
            print(f"请确保服务已启动: docker compose up -d")
            sys.exit(1)

        # 2. 创建知识库
        print("\n>>> 创建知识库...")
        resp = await client.post("/api/v1/knowledge-bases", json={
            "name": "默认知识库",
            "description": "RAG 和 LLM Wiki 技术文档",
        })
        resp.raise_for_status()
        kb = resp.json()
        kb_id = kb["id"]
        print(f"✓ 知识库已创建: {kb['name']} (ID: {kb_id})")

        # 3. 导入示例文档
        print("\n>>> 导入示例文档...")
        for i, doc in enumerate(SAMPLE_DOCS):
            print(f"  导入 [{i + 1}/{len(SAMPLE_DOCS)}]: {doc['title']}...")
            files = {
                "file": (f"{doc['title']}.md", doc["content"].encode("utf-8"), "text/markdown"),
            }
            resp = await client.post(
                f"/api/v1/knowledge-bases/{kb_id}/documents",
                files=files,
                data={"title": doc["title"]},
            )
            if resp.status_code == 200:
                doc_resp = resp.json()
                print(f"  ✓ 导入完成: {doc_resp['chunk_count']} 个片段")
            else:
                print(f"  ❌ 导入失败: {resp.text}")

        # 4. 测试搜索
        print("\n>>> 测试搜索...")
        resp = await client.post(
            f"/api/v1/knowledge-bases/{kb_id}/search",
            json={"query": "什么是 RAG？", "top_k": 3},
        )
        resp.raise_for_status()
        search_resp = resp.json()
        print(f"  搜索耗时: {search_resp['query_time_ms']}ms")
        for r in search_resp["results"]:
            print(f"  - [{r['score']:.4f}] {r['document_title']}: {r['content'][:80]}...")

        # 5. 测试问答
        print("\n>>> 测试问答...")
        resp = await client.post(
            f"/api/v1/knowledge-bases/{kb_id}/query",
            json={"query": "LLM Wiki 有哪些核心操作？", "top_k": 3},
        )
        resp.raise_for_status()
        query_resp = resp.json()
        print(f"  问答耗时: {query_resp['query_time_ms']}ms")
        print(f"  回答: {query_resp['answer'][:300]}...")

        # 6. 查看 Wiki
        print("\n>>> 查看 Wiki 页面...")
        resp = await client.get(f"/api/v1/knowledge-bases/{kb_id}/wiki/pages")
        resp.raise_for_status()
        wiki_resp = resp.json()
        print(f"  Wiki 页面数: {wiki_resp['total']}")
        for p in wiki_resp["pages"]:
            print(f"  - {p['category']}/{p['id']}.md")

    print("\n✓ 测试数据导入完成！")
    print(f"  访问 Web UI: http://localhost:3000")
    print(f"  访问 API:    http://localhost:8000/docs")


if __name__ == "__main__":
    asyncio.run(main())
