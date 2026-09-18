"""Tier1 分类+打分 prompt 构建测试:system + user prompt 模板。

纯逻辑测试,验证 prompt 结构与变量注入。
"""
import pytest

from src.ai.prompting.classification import (
    analysis_system_prompt,
    analysis_user_prompt,
)


@pytest.fixture
def category_tree_json() -> str:
    """模拟 CategoryRegistry.category_tree_json() 输出。"""
    return (
        '{\n'
        '  "ai-research": {"display_name": "AI 研究", "threshold": 7.0, "children": ["ai-vendor", "ai-researcher", "ai-papers"]},\n'
        '  "systems": {"display_name": "系统工程", "threshold": 5.0, "children": ["eng-blog", "framework"]}\n'
        '}'
    )


def test_system_prompt_contains_category_tree(category_tree_json: str):
    """system prompt 注入分类树 JSON。"""
    prompt = analysis_system_prompt(category_tree_json)
    assert "ai-research" in prompt
    assert "ai-vendor" in prompt
    assert "systems" in prompt


def test_system_prompt_instructs_json_output(category_tree_json: str):
    """system prompt 要求输出 JSON 对象。"""
    prompt = analysis_system_prompt(category_tree_json)
    assert "JSON" in prompt or "json" in prompt
    assert "category" in prompt
    assert "score" in prompt
    assert "summary" in prompt
    assert "tags" in prompt


def test_system_prompt_specifies_score_range(category_tree_json: str):
    """system prompt 说明 0-10 评分标准。"""
    prompt = analysis_system_prompt(category_tree_json)
    assert "0" in prompt and "10" in prompt


def test_system_prompt_includes_category_hint_rule(category_tree_json: str):
    """system prompt 说明源 category hint 可 override 规则。"""
    prompt = analysis_system_prompt(category_tree_json)
    assert "override" in prompt.lower() or "hint" in prompt.lower() or "源" in prompt


def test_user_prompt_contains_title():
    """user prompt 包含条目标题。"""
    prompt = analysis_user_prompt(
        title="GPT-5 发布",
        content="OpenAI 发布 GPT-5,支持多模态推理",
        feed_name="OpenAI News",
        category_hint="ai-research/ai-vendor",
    )
    assert "GPT-5 发布" in prompt


def test_user_prompt_contains_content():
    """user prompt 包含条目内容(截取)。"""
    long_content = "技术细节" * 200
    prompt = analysis_user_prompt(
        title="测试",
        content=long_content,
        feed_name="Feed",
        category_hint="ai-research/ai-papers",
        max_chars=500,
    )
    assert "技术细节" in prompt
    assert len(prompt) < len(long_content) * 2  # 内容被截取


def test_user_prompt_contains_category_hint():
    """user prompt 包含源级 category hint。"""
    prompt = analysis_user_prompt(
        title="测试",
        content="内容",
        feed_name="Anthropic",
        category_hint="ai-research/ai-vendor",
    )
    assert "ai-research/ai-vendor" in prompt
    assert "Anthropic" in prompt


def test_user_prompt_handles_none_category_hint():
    """category_hint=None 时 prompt 正常生成,提示 AI 自主分类。"""
    prompt = analysis_user_prompt(
        title="测试",
        content="内容",
        feed_name="Unknown",
        category_hint=None,
    )
    assert "测试" in prompt
    assert "Unknown" in prompt


def test_user_prompt_handles_empty_content():
    """空内容时 prompt 正常生成。"""
    prompt = analysis_user_prompt(
        title="空内容",
        content="",
        feed_name="Feed",
        category_hint=None,
    )
    assert "空内容" in prompt
