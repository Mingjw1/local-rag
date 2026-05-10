"""文档解析器单元测试"""

import sys, tempfile, os
sys.path.insert(0, "..")

from app.pipeline.parsers import parse_document


def test_parse_markdown():
    """解析 Markdown 文件"""
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
        f.write("# Test\n\nHello world.")
        fname = f.name
    try:
        result = parse_document(fname, "text/markdown")
        assert result is not None
        assert "# Test" in result
        assert "Hello world." in result
    finally:
        os.unlink(fname)


def test_parse_text():
    """解析文本文件"""
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
        f.write("Just plain text.")
        fname = f.name
    try:
        result = parse_document(fname, "text/plain")
        assert result == "Just plain text."
    finally:
        os.unlink(fname)


def test_parse_nonexistent():
    """不存在的文件返回 None"""
    result = parse_document("/nonexistent/file.md", "text/markdown")
    assert result is None


def test_parse_unsupported():
    """不支持的文件类型尝试解析"""
    with tempfile.NamedTemporaryFile(suffix=".xyz", mode="w", delete=False) as f:
        f.write("unknown format")
        fname = f.name
    try:
        result = parse_document(fname, "application/octet-stream")
        assert result is None  # 不支持的类型
    finally:
        os.unlink(fname)


if __name__ == "__main__":
    test_parse_markdown()
    test_parse_text()
    test_parse_nonexistent()
    test_parse_unsupported()
    print("✓ 所有解析器测试通过")
