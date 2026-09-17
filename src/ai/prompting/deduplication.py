"""Tier2 主题去重 prompt:按分类分组,让 LLM 判断同组内是否为同一事件,输出聚类 JSON。

借鉴 Horizon merge_topic_duplicates,但按分类分组降低 prompt 大小。
"""

from __future__ import annotations


def topic_dedup_system_prompt() -> str:
    """构建主题去重 system prompt:要求输出 ID 聚类数组的数组。

    输出格式示例:[["id1", "id2"], ["id3"], ["id4", "id5", "id6"]]
    每个子数组是同一事件的不同报道,孤立条目单独成组。
    """
    return """你是新闻去重分析员。判断给定条目中哪些是同一事件的不同报道。

## 任务
将同一事件的不同报道归为一组。判断依据:
- 相同事件/发布/论文 → 同一组
- 仅主题相关但事件不同 → 不同组
- 孤立条目(无同事件报道)单独成组

## 输出格式
输出 JSON 数组,每个元素是同一事件的条目 ID 数组。所有输入条目必须出现在某个子数组中。

示例:
输入 4 条,其中 2 条是同一事件:
[["id1", "id2"], ["id3"], ["id4"]]

只输出 JSON,不要其他文字。"""


def topic_dedup_user_prompt(category: str, items_summary: str) -> str:
    """构建主题去重 user prompt:分类名 + 条目摘要列表。

    items_summary 应为预格式化的 "[ID: xxx] 标题 摘要" 列表。
    """
    items_section = items_summary if items_summary.strip() else "(无条目)"
    return f"""分类:{category}

条目:
{items_section}

请判断哪些条目是同一事件的不同报道,输出 ID 聚类的 JSON 数组。所有条目 ID 必须来自上述输入。"""
