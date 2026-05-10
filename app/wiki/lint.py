"""Lint 检查 — 知识库健康检查"""

from app.wiki.engine import WikiEngine


async def run_lint(engine: WikiEngine) -> dict:
    """执行 lint 检查，返回报告"""
    pages = engine.list_pages()
    issues = []

    # 1. 孤儿页检查（零入链引用的页面）
    orphan_pages = _check_orphans(pages, engine)
    for p in orphan_pages:
        issues.append({"type": "orphan", "severity": "warn", "page": p["id"], "message": "零入链引用"})

    # 2. 断裂链接检查
    broken_links = _check_broken_links(engine)
    for link in broken_links:
        issues.append({"type": "broken_link", "severity": "error", "page": link["page"], "message": f"断裂链接: {link['link']}"})

    # 3. 检查 index.md 一致性
    index_issues = _check_index_consistency(pages, engine)
    issues.extend(index_issues)

    # 写入 log
    report = f"""## [{__import__('datetime').datetime.utcnow().strftime('%Y-%m-%d %H:%M')}] lint | 健康检查报告
- ✅ 总页面数: {len(pages)}
- ❌ 孤儿页: {len(orphan_pages)}
- ❌ 断裂链接: {len(broken_links)}
- ❌ Index 不一致: {len(index_issues)}
"""
    for issue in issues:
        report += f"  - {issue['severity'].upper()}: [{issue['type']}] {issue.get('message', '')}\n"

    with open(engine.log_file, "a", encoding="utf-8") as f:
        f.write(report + "\n")

    return {"issues": issues, "total_pages": len(pages), "report": report}


def _check_orphans(pages: list, engine: WikiEngine) -> list:
    """检查孤儿页（没有任何页面链接到它）"""
    if not pages:
        return []

    # 收集所有页面引用
    all_content = ""
    for p in pages:
        content = engine.read_page(p["id"])
        if content:
            all_content += content + "\n"

    orphans = []
    for p in pages:
        # 检查是否有其他页面链接到此页
        link_pattern = f"({p['id']})"  # markdown 链接
        # 简单检查：文件名是否出现在其他页面内容中
        ref_count = all_content.count(f"{p['id']}.md") + all_content.count(f"]({p['id']})")
        if ref_count == 0 and p["category"] not in ("sources",):
            # sources 目录下的页面不强制要求被引用
            orphans.append(p)

    return orphans


def _check_broken_links(engine: WikiEngine) -> list:
    """检查断裂的内部链接"""
    broken = []
    for page in engine.list_pages():
        content = engine.read_page(page["id"])
        if not content:
            continue
        # 查找 markdown 链接
        import re
        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
        for title, link in links:
            if link.startswith("./") or link.startswith("../"):
                # 内部链接，检查目标文件是否存在
                from pathlib import Path
                target = (engine.wiki_path / link).resolve()
                if not target.exists():
                    broken.append({"page": page["id"], "link": link, "title": title})
    return broken


def _check_index_consistency(pages: list, engine: WikiEngine) -> list:
    """检查 index.md 是否与实际页面一致"""
    if not engine.index_file.exists():
        return [{"type": "missing_index", "severity": "error", "message": "index.md 不存在"}]

    index_content = engine.index_file.read_text(encoding="utf-8")
    issues = []

    # 检查是否有页面未在 index 中列出
    for p in pages:
        if p["id"] not in index_content:
            issues.append({
                "type": "missing_from_index",
                "severity": "warn",
                "page": p["id"],
                "message": f"页面 {p['id']} 未在 index.md 中列出",
            })

    return issues
