"""LLM Wiki Engine — 自动维护结构化知识库

三大操作：
- ingest: 文档导入后，自动生成/更新 wiki 页面
- query: 通过 wiki 索引加速搜索
- lint: 健康检查
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from app.core.config import settings


class WikiEngine:
    """Wiki 引擎 — 维护 per-tenant 的 markdown 知识库"""

    def __init__(self, kb_id: str):
        self.kb_id = kb_id
        wiki_config = settings.rag_config.get("wiki", {})
        base_path = wiki_config.get("base_path", "./data/wiki")
        self.wiki_path = Path(base_path) / kb_id
        self.pages_path = self.wiki_path / "pages"
        self.sources_path = self.pages_path / "sources"
        self.concepts_path = self.pages_path / "concepts"
        self.index_file = self.wiki_path / (wiki_config.get("index_file", "index.md"))
        self.log_file = self.wiki_path / (wiki_config.get("log_file", "log.md"))

        # 确保目录存在
        self.sources_path.mkdir(parents=True, exist_ok=True)
        self.concepts_path.mkdir(parents=True, exist_ok=True)
        (self.pages_path / "entities").mkdir(parents=True, exist_ok=True)
        (self.pages_path / "generated").mkdir(parents=True, exist_ok=True)

        # 初始化 index 和 log
        self._ensure_file(self.index_file, "# 知识库索引\n\n## 源文档 (Sources)\n\n## 概念 (Concepts)\n\n## 实体 (Entities)\n\n## 生成内容 (Generated)\n\n---\n*最后更新: -\n*")
        self._ensure_file(self.log_file, "# 变更日志\n\n")

    def _ensure_file(self, path: Path, default_content: str):
        """确保文件存在，不存在则用默认内容创建"""
        if not path.exists():
            path.write_text(default_content, encoding="utf-8")

    # === Ingest 操作 ===

    async def after_ingest(self, doc, chunks_text: List[str]):
        """文档导入后的 Wiki 更新"""
        from app.core.ollama_client import ollama_client

        # 1. 生成文档摘要
        source_page_title = self._safe_filename(doc.title)
        source_page_path = self.sources_path / f"{source_page_title}.md"

        # 用 LLM 生成摘要
        summary = await ollama_client.generate(
            prompt=f"请为以下文档生成一段 200 字以内的中文摘要，包括核心主题和关键内容：\n\n{doc.title}\n\n{chunks_text[0][:1000] if chunks_text else ''}",
            system="你是一个知识库管理员，为文档生成简洁的中文摘要。",
        )

        # 2. 生成/更新源文档页面
        source_content = f"""---
title: "{doc.title}"
type: source
created: {datetime.utcnow().isoformat()}
updated: {datetime.utcnow().isoformat()}
chunks: {len(chunks_text)}
file: {doc.source_info.get('filename', '')}
---

# {doc.title}

## 摘要

{summary}

## 内容片段

"""
        for i, chunk in enumerate(chunks_text[:5]):  # 前 5 块
            source_content += f"\n### 片段 {i + 1}\n\n{chunk[:500]}\n"
        if len(chunks_text) > 5:
            source_content += f"\n*...共 {len(chunks_text)} 个片段*\n"

        source_page_path.write_text(source_content, encoding="utf-8")

        # 3. 追加 log
        log_entry = f"""## [{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}] ingest | {doc.title}
- 类型: {doc.content_type}
- 片段数: {len(chunks_text)}
- 状态: ready
"""
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")

        # 4. 更新 index
        self._update_index(doc.title, "sources", source_page_title)

    def _update_index(self, title: str, category: str, page_id: str):
        """在 index.md 中追加或更新条目"""
        content = self.index_file.read_text(encoding="utf-8")

        link = f"[{title}](./pages/{category}/{page_id}.md)"
        line = f"| {link} | {datetime.utcnow().strftime('%Y-%m-%d')} |"
        entry = f"| {link} | | {datetime.utcnow().strftime('%Y-%m-%d')} | 1 |\n"

        # 找到对应分类部分的末尾，追加条目
        section_header = f"## {category}"
        # 简单实现：直接追加到文件末尾前一行
        content = content.rstrip()
        content += f"\n{entry}"

        # 更新最后更新时间
        content = re.sub(
            r'\*最后更新: .+?\*',
            f'*最后更新: {datetime.utcnow().strftime("%Y-%m-%d")}*',
            content,
        )

        self.index_file.write_text(content, encoding="utf-8")

    # === Query 操作 ===

    def search_index(self, keyword: str) -> List[dict]:
        """在 wiki index 中搜索（轻量文本搜索）"""
        if not self.index_file.exists():
            return []

        content = self.index_file.read_text(encoding="utf-8")
        results = []
        for line in content.split("\n"):
            if keyword.lower() in line.lower() and line.startswith("| ["):
                # 解析: | [title](./path) | summary | date | count |
                match = re.match(r'\|\s*\[(.+?)\]\((.+?)\)', line)
                if match:
                    results.append({
                        "title": match.group(1),
                        "path": str(self.wiki_path.parent / match.group(2)),
                        "line": line,
                    })
        return results

    # === Lint 操作 ===

    def list_pages(self) -> List[dict]:
        """列出所有 wiki 页面"""
        pages = []
        for path in self.pages_path.rglob("*.md"):
            if path.is_file():
                pages.append({
                    "id": path.stem,
                    "path": str(path.relative_to(self.wiki_path)),
                    "category": path.parent.name,
                    "size": path.stat().st_size,
                    "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                })
        return pages

    def read_page(self, page_id: str) -> Optional[str]:
        """根据 ID 读取页面内容"""
        for path in self.pages_path.rglob(f"{page_id}.md"):
            return path.read_text(encoding="utf-8")
        return None

    @staticmethod
    def _safe_filename(name: str) -> str:
        """将标题转为安全的文件名"""
        name = re.sub(r'[^\w\s-]', '', name)
        name = re.sub(r'[-\s]+', '-', name)
        return name[:100].strip("-").lower()
