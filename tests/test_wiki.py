"""Wiki Engine 单元测试"""

import sys, tempfile, os
sys.path.insert(0, "..")

from app.wiki.engine import WikiEngine


def test_safe_filename():
    """文件名净化"""
    assert WikiEngine._safe_filename("Hello World") == "hello-world"
    assert WikiEngine._safe_filename("测试文档!@#") == "测试文档"
    assert WikiEngine._safe_filename("") == ""


def test_list_pages_empty():
    """空知识库列出页面"""
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        from app.core.config import settings
        settings.rag_config["wiki"] = {"base_path": tmp}
        engine = WikiEngine("test-kb")
        pages = engine.list_pages()
        assert pages == []


if __name__ == "__main__":
    test_safe_filename()
    print("✓ 所有 Wiki 测试通过")
