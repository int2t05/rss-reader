"""AI JSON 解析测试:parse_json_response 多策略从 LLM 响应中提取 JSON。

纯逻辑测试,无网络无 LLM,用真实 LLM 响应样本验证。
"""
import pytest

from src.ai.utils import parse_json_response


def test_parse_clean_json():
    """干净的 JSON 字符串直接解析。"""
    resp = '{"category": "ai-research/ai-papers", "score": 8.5, "summary": "新论文"}'
    result = parse_json_response(resp)
    assert result is not None
    assert result["category"] == "ai-research/ai-papers"
    assert result["score"] == 8.5


def test_parse_json_in_code_block():
    """LLM 常用 ```json 代码块包裹,应能提取。"""
    resp = '```json\n{"category": "research/arxiv-cs", "score": 7.0, "summary": "论文"}\n```'
    result = parse_json_response(resp)
    assert result is not None
    assert result["category"] == "research/arxiv-cs"


def test_parse_json_with_leading_text():
    """JSON 前有说明文字,应提取首个 JSON 对象。"""
    resp = 'Here is the analysis:\n{"category": "systems/eng-blog", "score": 6.0, "summary": "博客"}\nDone.'
    result = parse_json_response(resp)
    assert result is not None
    assert result["category"] == "systems/eng-blog"
    assert result["score"] == 6.0


def test_parse_json_with_trailing_text():
    """JSON 后有尾随文字,应提取 JSON 对象。"""
    resp = '{"category": "tech-news/cn-news", "score": 5.5, "summary": "新闻"}\n\n以上是分析结果。'
    result = parse_json_response(resp)
    assert result is not None
    assert result["summary"] == "新闻"


def test_parse_malformed_json_returns_none():
    """格式错误的 JSON 返回 None,不抛异常。"""
    resp = '{"category": "broken", "score": '
    result = parse_json_response(resp)
    assert result is None


def test_parse_empty_returns_none():
    """空字符串返回 None。"""
    assert parse_json_response("") is None
    assert parse_json_response("   ") is None


def test_parse_no_json_returns_none():
    """无 JSON 内容返回 None。"""
    assert parse_json_response("This is just text without any JSON.") is None


def test_parse_nested_json_object():
    """嵌套 JSON 对象可解析。"""
    resp = '{"category": "ai-research/ai-papers", "tags": ["llm", "safety"], "score": 9.0}'
    result = parse_json_response(resp)
    assert result is not None
    assert result["tags"] == ["llm", "safety"]
    assert result["score"] == 9.0


def test_parse_json_with_newlines_in_strings():
    """JSON 字符串值含换行,解析器容忍。"""
    resp = '{"summary": "第一行\\n第二行", "score": 5.0}'
    result = parse_json_response(resp)
    assert result is not None
    assert "第一行" in result["summary"]


def test_parse_returns_dict_type():
    """返回值是 dict 类型(非 str/list)。"""
    result = parse_json_response('{"a": 1}')
    assert isinstance(result, dict)


def test_parse_array_returns_none():
    """顶层是数组(非对象)时返回 None(契约要求返回 dict)。"""
    result = parse_json_response('[1, 2, 3]')
    assert result is None
