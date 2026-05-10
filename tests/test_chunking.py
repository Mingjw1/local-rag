"""分块策略单元测试"""

import sys
sys.path.insert(0, "..")

from app.pipeline.chunking import chunk_text, chunk_document


def test_recursive_chunk_short():
    """短文本不分块"""
    text = "这是一个短文本。"
    chunks = chunk_text(text, "recursive")
    assert len(chunks) == 1
    assert chunks[0] == text.strip()


def test_recursive_chunk_long():
    """长文本被正确切分"""
    text = "段落一。" * 200
    chunks = chunk_text(text, "recursive")
    assert len(chunks) > 1


def test_code_aware_chunk():
    """代码块不被分割"""
    text = """# 标题

普通文本段落。

```python
def hello():
    print("hello world")
    return 42
```

更多普通文本。"""
    chunks = chunk_document(text, "text/markdown")
    assert len(chunks) >= 2
    # 至少有一个 chunk 包含代码块
    code_chunks = [c for c in chunks if "```" in c]
    assert len(code_chunks) >= 1


def test_semantic_chunk():
    """语义分块按句子边界"""
    text = "第一句。第二句！第三句？第四句。第五句。"
    chunks = chunk_text(text, "semantic")
    assert len(chunks) >= 1
    for c in chunks:
        assert c.strip()  # 非空


def test_empty_text():
    """空文本返回空列表"""
    chunks = chunk_text("", "recursive")
    assert chunks == []


if __name__ == "__main__":
    test_recursive_chunk_short()
    test_recursive_chunk_long()
    test_code_aware_chunk()
    test_semantic_chunk()
    test_empty_text()
    print("✓ 所有分块测试通过")
