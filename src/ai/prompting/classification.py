"""Tier1 分类+打分 prompt 构建:system prompt 注入分类树 + 评分标准,user prompt 注入条目内容。

合并分类与打分为单次 LLM 调用(借鉴 Horizon 但简化为一次调用)。
"""

from __future__ import annotations

_DEFAULT_MAX_CHARS = 1000


def analysis_system_prompt(category_tree_json: str) -> str:
    """构建 Tier1 system prompt:分类树 + 评分标准 + JSON 输出契约。

    示例:
        prompt = analysis_system_prompt(registry.category_tree_json())
    """
    return f"""你是技术信息分类器。将条目归入以下分类树之一,并打分(0-10)。

## 分类树
{category_tree_json}

## 评分标准(0-10)
- 9-10: 重大突破 / 重要发布(如 GPT-5 发布、arXiv 顶会最佳论文)
- 7-8:  有价值的技术动态 / 研究发现
- 5-6:  一般性更新 / 教程 / 观点
- 3-4:  低价值 / 营销 / 重复
- 0-2:  无关 / 垃圾

## 源 category hint
条目可能附带源级 category hint(如 "ai-research/ai-vendor")。默认采用 hint,
但如果内容明显跨类,请 override 为更合适的分类。

## 输出格式
输出 JSON 对象,包含以下字段:
{{
  "category": "分类路径,如 ai-research/ai-papers",
  "score": 8.5,
  "summary": "一句话中文摘要",
  "tags": ["标签1", "标签2", "标签3"]
}}

只输出 JSON,不要其他文字。"""


def analysis_user_prompt(
    title: str,
    content: str,
    feed_name: str,
    category_hint: str | None,
    max_chars: int = _DEFAULT_MAX_CHARS,
) -> str:
    """构建 Tier1 user prompt:条目标题 + 内容截取 + 源信息。

    content 超过 max_chars 时截取前 max_chars 字符。
    """
    truncated = content[:max_chars] if content else ""
    hint_line = f"类别提示:{category_hint}" if category_hint else "类别提示:(无,AI 自主分类)"
    return f"""标题:{title}
内容:{truncated}
来源:{feed_name}
{hint_line}"""
