"""Wiki API 路由"""

from fastapi import APIRouter, Depends, HTTPException

from app.wiki.engine import WikiEngine
from app.wiki.lint import run_lint

router = APIRouter(tags=["wiki"])


@router.post("/knowledge-bases/{kb_id}/wiki/lint")
async def trigger_lint(kb_id: str):
    """触发 Lint 检查"""
    engine = WikiEngine(kb_id)
    report = await run_lint(engine)
    return report


@router.get("/knowledge-bases/{kb_id}/wiki/pages")
async def list_wiki_pages(kb_id: str):
    """列出 Wiki 页面"""
    engine = WikiEngine(kb_id)
    pages = engine.list_pages()
    return {"pages": pages, "total": len(pages)}


@router.get("/knowledge-bases/{kb_id}/wiki/pages/{page_id}")
async def get_wiki_page(kb_id: str, page_id: str):
    """获取 Wiki 页面内容"""
    engine = WikiEngine(kb_id)
    content = engine.read_page(page_id)
    if content is None:
        raise HTTPException(404, "Page not found")
    return {"id": page_id, "content": content}
