"""normalize_text 单元测试"""

import sys
sys.path.insert(0, "..")

from app.routers.search import normalize_text


def test_normalize_token_split_latin():
    """修复 tokenizer 导致的分词断裂: R AG → RAG + 中英文间距"""
    assert normalize_text("这是一个R AG技术") == "这是一个 RAG 技术"


def test_normalize_subword_split():
    """修复子词分割: Retrieval 被拆成 Ret rie val"""
    result = normalize_text("这是Ret rie val技术")
    assert "Retrieval" in result
    assert "Retrieval" in result


def test_normalize_cjk_latin_spacing():
    """中英文之间插入空格: 你好World → 你好 World"""
    assert normalize_text("你好World") == "你好 World"
    assert normalize_text("Hello世界") == "Hello 世界"


def test_normalize_no_english_damage():
    """纯英文文本不被 CJK 逻辑破坏"""
    text = "hello world this is a test"
    assert normalize_text(text) == text


def test_normalize_cjk_punctuation_spacing():
    """修复中文标点前的空格"""
    assert normalize_text("你好 。") == "你好。"
    assert normalize_text("你好 ！") == "你好！"
    assert normalize_text("你好 ？") == "你好？"


def test_normalize_multi_space():
    """多余空格合并"""
    assert normalize_text("hello   world") == "hello world"


def test_normalize_short_text():
    """短文本处理"""
    assert normalize_text("") == ""
    assert normalize_text("  ") == ""
    assert normalize_text("hello") == "hello"


def test_normalize_cjk_pure():
    """纯中文文本不被修改"""
    assert normalize_text("这是一个测试文本") == "这是一个测试文本"


def test_normalize_mixed_with_source():
    """混合引用场景"""
    text = "根据 R AG 技术 ，我们可以实现 Ret rie val 增强生成 。"
    result = normalize_text(text)
    assert "RAG" in result
    assert "Retrieval" in result
    assert "，" in result
    assert "。" in result
