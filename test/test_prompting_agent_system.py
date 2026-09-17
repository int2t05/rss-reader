"""Tier3 agent 系统 prompt 构建测试:纯逻辑验证。"""
import pytest

from src.ai.prompting.agent_system import (
    agent_system_prompt,
    fallback_result_prompt,
)


def test_agent_system_prompt_contains_category():
    """agent 系统 prompt 注入分类名与 display_name。"""
    prompt = agent_system_prompt(
        category="ai-research/ai-papers",
        display_name="AI 研究",
    )
    assert "ai-research/ai-papers" in prompt or "AI 研究" in prompt


def test_agent_system_prompt_instructs_json_output():
    """prompt 要求输出结构化 JSON。"""
    prompt = agent_system_prompt("ai-research/ai-papers", "AI 研究")
    assert "JSON" in prompt or "json" in prompt
    # 必含字段
    assert "title" in prompt
    assert "summary" in prompt
    assert "background" in prompt
    assert "impact" in prompt
    assert "references" in prompt
    assert "tags" in prompt


def test_agent_system_prompt_includes_tool_descriptions():
    """prompt 包含可用工具描述:web_search + web_fetch。"""
    prompt = agent_system_prompt("systems/eng-blog", "系统工程")
    assert "web_search" in prompt
    assert "web_fetch" in prompt


def test_agent_system_prompt_specifies_crag_rules():
    """prompt 说明 CRAG 行为指引:strong 跳过/weak 强制联网。"""
    prompt = agent_system_prompt("ai-research/ai-papers", "AI 研究")
    assert "strong" in prompt or "weak" in prompt or "充分" in prompt


def test_agent_system_prompt_specifies_quality_rules():
    """prompt 包含质量规则:事实与推断分开、来源分级。"""
    prompt = agent_system_prompt("ai-research/ai-papers", "AI 研究")
    assert "事实" in prompt or "推断" in prompt or "官方文档" in prompt


def test_agent_system_prompt_handles_empty_display_name():
    """display_name 为空时 prompt 仍正常生成。"""
    prompt = agent_system_prompt("ai-research/ai-papers", "")
    assert "ai-research/ai-papers" in prompt
    assert "JSON" in prompt or "json" in prompt


def test_fallback_result_prompt_instructs_minimal_json():
    """fallback_result_prompt 指示输出最小 JSON(title + summary)。"""
    prompt = fallback_result_prompt()
    assert "JSON" in prompt or "json" in prompt
    assert "title" in prompt
    assert "summary" in prompt
