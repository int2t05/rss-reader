"""Markdown 简报渲染:按分类组织,每条目含 Tier1 + Tier3 字段。

输出双语格式:lang=zh 用中文标题,lang=en 用英文标题。
渲染顺序:日期标题 → 统计 → 按分类分节 → 每分类下条目列表。
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from src.models import ContentItem

_ZH_TITLES = {
    "title": "每日简报",
    "stats": "统计",
    "items": "条目",
    "score": "分数",
    "summary": "摘要",
    "background": "背景",
    "impact": "影响",
    "references": "参考",
    "tags": "标签",
    "source": "来源",
    "no_items": "今日无精选条目。",
}

_EN_TITLES = {
    "title": "Daily Briefing",
    "stats": "Stats",
    "items": "items",
    "score": "Score",
    "summary": "Summary",
    "background": "Background",
    "impact": "Impact",
    "references": "References",
    "tags": "Tags",
    "source": "Source",
    "no_items": "No selected items today.",
}


def _labels(lang: str) -> dict[str, str]:
    """根据语言返回标签字典。"""
    return _EN_TITLES if lang == "en" else _ZH_TITLES


def render_markdown(items: list[ContentItem], date: datetime, lang: str = "zh") -> str:
    """渲染 Markdown 简报:按分类分节,每条目含 title/score/summary/深层字段。

    示例:
        md = render_markdown(items, date=datetime.now(), lang="zh")
    """
    labels = _labels(lang)
    date_str = date.strftime("%Y-%m-%d")

    lines: list[str] = []
    lines.append(f"# {labels['title']} · {date_str}")
    lines.append("")

    if not items:
        lines.append(labels["no_items"])
        return "\n".join(lines)

    # 统计
    lines.append(f"**{labels['stats']}**: {len(items)} {labels['items']}")
    lines.append("")

    # 按分类分组(按 analysis.category_path 的父分类)
    grouped: dict[str, list[ContentItem]] = defaultdict(list)
    for item in items:
        path = (
            item.processing.analysis.category_path
            if item.processing and item.processing.analysis
            else (item.category or "unknown")
        )
        # 按父分类分组(ai-research/ai-papers → ai-research)
        parent = path.split("/", 1)[0] if "/" in path else path
        grouped[parent].append(item)

    for cat in sorted(grouped.keys()):
        cat_items = grouped[cat]
        lines.append(f"## {cat}")
        lines.append("")

        for item in cat_items:
            _render_item(lines, item, labels)
            lines.append("")

    return "\n".join(lines)


def _render_item(lines: list[str], item: ContentItem, labels: dict[str, str]) -> None:
    """渲染单条目:标题 + 分数 + 摘要 + 可选深层字段。"""
    analysis = item.processing.analysis if item.processing and item.processing.analysis else None
    deep = item.processing.deep_analysis if item.processing and item.processing.deep_analysis else None

    # 标题行(含链接)
    # TODO: title/url 未转义 Markdown 特殊字符(]、)),含特殊字符的标题/URL 会破坏链接语法
    title = (deep.title if deep and deep.title else item.title) or "Untitled"
    url = item.url or "#"
    score_str = f"{analysis.score:.1f}" if analysis and analysis.score is not None else "-"
    lines.append(f"### [{title}]({url})")
    lines.append("")
    lines.append(f"- **{labels['score']}**: {score_str}")

    # 摘要(优先用深层 summary,其次 Tier1 summary)
    summary = (deep.summary if deep and deep.summary else None) or (analysis.summary if analysis else None)
    if summary:
        lines.append(f"- **{labels['summary']}**: {summary}")

    # 深层字段(仅在 Tier3 结果存在时)
    if deep:
        if deep.background:
            lines.append(f"- **{labels['background']}**: {deep.background}")
        if deep.impact:
            lines.append(f"- **{labels['impact']}**: {deep.impact}")
        if deep.references:
            ref_lines = [f"  - [{r.title or r.url}]({r.url})" for r in deep.references]
            lines.append(f"- **{labels['references']}**:")
            lines.extend(ref_lines)
        if deep.tags:
            lines.append(f"- **{labels['tags']}: {', '.join(deep.tags)}**")
    elif analysis and analysis.tags:
        lines.append(f"- **{labels['tags']}: {', '.join(analysis.tags)}**")
