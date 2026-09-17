"""内容分块与采样测试:split_content / select_content。

纯逻辑测试,无网络无 LLM。
"""
import pytest

from src.processing.content import select_content, split_content


def test_split_content_main_and_comments():
    """split_content 分离正文与评论(以 --- 分隔)。"""
    text = "正文第一段。\n\n---\n\n评论 A\n评论 B"
    parts = split_content(text)
    assert parts.main == "正文第一段。"
    assert "评论 A" in parts.comments
    assert "评论 B" in parts.comments


def test_split_content_no_separator():
    """无分隔符时,全部归为 main,comments 为空。"""
    text = "只有正文,无分隔符。"
    parts = split_content(text)
    assert parts.main == text
    assert parts.comments == ""


def test_split_content_empty():
    """空字符串:main 与 comments 均为空。"""
    parts = split_content("")
    assert parts.main == ""
    assert parts.comments == ""


def test_split_content_multiple_separators():
    """多个分隔符:首个分隔符之前为 main,之后全部为 comments。"""
    text = "正文\n---\n评论1\n---\n评论2"
    parts = split_content(text)
    assert parts.main == "正文"
    assert "评论1" in parts.comments
    assert "评论2" in parts.comments


def test_select_content_under_max_chars():
    """内容长度 ≤ max_chars 时原样返回。"""
    result = select_content("短内容", max_chars=1000, sampling="head")
    assert result == "短内容"


def test_select_content_head_sampling():
    """head 采样:截取前 max_chars 字符。"""
    text = "0123456789" * 100  # 1000 字符
    result = select_content(text, max_chars=100, sampling="head")
    assert len(result) == 100
    assert result == text[:100]


def test_select_content_tail_sampling():
    """tail 采样:截取末尾 max_chars 字符。"""
    text = "0123456789" * 100
    result = select_content(text, max_chars=50, sampling="tail")
    assert len(result) == 50
    assert result == text[-50:]


def test_select_content_head_tail_sampling():
    """head_tail 采样:前半 + 省略 + 后半,总长不超过 max_chars。"""
    text = "0123456789" * 100  # 1000 字符
    result = select_content(text, max_chars=100, sampling="head_tail")
    assert len(result) <= 100
    assert result.startswith("0123456789")
    assert result.endswith("0123456789")


def test_select_content_empty_input():
    """空内容返回空字符串。"""
    assert select_content("", max_chars=100, sampling="head") == ""


def test_select_content_max_chars_zero():
    """max_chars=0 返回空字符串。"""
    assert select_content("内容", max_chars=0, sampling="head") == ""


def test_select_content_unknown_sampling_defaults_head():
    """未知 sampling 策略默认 head。"""
    text = "0123456789" * 100
    result = select_content(text, max_chars=50, sampling="unknown")
    assert result == text[:50]
