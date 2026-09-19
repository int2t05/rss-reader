"""Tier2 主题去重 prompt 构建测试:纯逻辑验证。"""

from src.ai.prompting.deduplication import topic_dedup_system_prompt, topic_dedup_user_prompt


def test_system_prompt_instructs_clustering():
    """system prompt 要求判断同一事件并输出聚类 JSON。"""
    prompt = topic_dedup_system_prompt()
    assert "同一" in prompt or "same" in prompt.lower()
    assert "JSON" in prompt or "json" in prompt
    assert "数组" in prompt or "array" in prompt.lower()


def test_system_prompt_specifies_output_format():
    """system prompt 说明输出格式为 ID 列表的数组。"""
    prompt = topic_dedup_system_prompt()
    # 应包含示例 JSON 格式
    assert "[" in prompt and "]" in prompt


def test_user_prompt_contains_category_name():
    """user prompt 注入分类名。"""
    prompt = topic_dedup_user_prompt(category="ai-research", items_summary="条目列表...")
    assert "ai-research" in prompt


def test_user_prompt_contains_items_list():
    """user prompt 包含条目摘要列表。"""
    items_summary = "1. [ID: abc] 标题A 摘要A\n2. [ID: def] 标题B 摘要B"
    prompt = topic_dedup_user_prompt(category="systems", items_summary=items_summary)
    assert "标题A" in prompt
    assert "标题B" in prompt
    assert "abc" in prompt


def test_user_prompt_handles_empty_items():
    """空条目列表 prompt 正常生成。"""
    prompt = topic_dedup_user_prompt(category="ai-research", items_summary="")
    assert "ai-research" in prompt


def test_user_prompt_includes_id_reference():
    """user prompt 强调返回的 ID 必须来自输入条目。"""
    items_summary = "1. [ID: abc] 标题A"
    prompt = topic_dedup_user_prompt(category="ai-research", items_summary=items_summary)
    assert "ID" in prompt or "id" in prompt
