"""AI JSON 解析测试:parse_json_response / parse_json_array_response 多策略从 LLM 响应中提取 JSON。

纯逻辑测试,无网络无 LLM,用真实 LLM 响应样本验证。
"""
import pytest

from src.ai.utils import parse_json_array_response, parse_json_response


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


def test_parse_two_objects_returns_first():
    """响应含两个 JSON 对象时,提取首个(括号配对,不贪婪吞掉中间)。"""
    resp = '{"a": 1} 一些文字 {"b": 2}'
    result = parse_json_response(resp)
    assert result is not None
    assert result == {"a": 1}


def test_parse_nested_braces_in_strings():
    """JSON 字符串值内含 { } 不影响括号配对。"""
    resp = '{"summary": "函数 {key: val} 描述", "score": 7.0}'
    result = parse_json_response(resp)
    assert result is not None
    assert result["score"] == 7.0
    assert "{key: val}" in result["summary"]


def test_parse_array_response_clean():
    """干净的 JSON 数组直接解析。"""
    result = parse_json_array_response('[["id1", "id2"], ["id3"]]')
    assert result == [["id1", "id2"], ["id3"]]


def test_parse_array_response_in_code_block():
    """LLM 用 ```json 代码块包裹数组时,应能提取。"""
    resp = '```json\n[["id1", "id2"], ["id3"]]\n```'
    result = parse_json_array_response(resp)
    assert result == [["id1", "id2"], ["id3"]]


def test_parse_array_response_with_leading_text():
    """数组前有说明文字,应提取首个数组。"""
    resp = '聚类结果:\n[["id1"], ["id2", "id3"]]\n完成。'
    result = parse_json_array_response(resp)
    assert result == [["id1"], ["id2", "id3"]]


def test_parse_array_response_object_returns_none():
    """顶层是对象(非数组)时返回 None(契约要求返回 list)。"""
    result = parse_json_array_response('{"a": 1}')
    assert result is None


def test_parse_array_response_empty_returns_none():
    """空字符串返回 None。"""
    assert parse_json_array_response("") is None
    assert parse_json_array_response("无 JSON") is None
