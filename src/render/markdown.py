"""Markdown 简报渲染:按分类组织,每条目含 Tier1 字段(title/score/summary/tags)。

渲染顺序:日期标题 → 统计 → 按分类分节 → 每分类下条目列表。
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from urllib.parse import quote, urlsplit

from src.models import ContentItem

# 简报各部分中文标签
_LABELS = {
    "title": "每日简报",
    "stats": "统计",
    "items": "条目",
    "score": "分数",
    "summary": "摘要",
    "tags": "标签",
    "source": "来源",
    "no_items": "今日无精选条目。",
}


def _plain_markdown_text(text: str) -> str:
    """把外部标题与模型摘要作为纯文本写入 Markdown，不接受 HTML 或嵌套链接。"""
    text = " ".join(text.split())
    return (
        text.replace("\\", "\\\\")
        .replace("[", r"\[")
        .replace("]", r"\]")
        .replace("(", r"\(")
        .replace(")", r"\)")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _escape_link_text(text: str) -> str:
    """转义链接标签中的 Markdown 分隔符，同时保留标题的可见文本。"""
    return _plain_markdown_text(text)


def _escape_link_url(url: str) -> str:
    """只接受绝对 HTTP(S) 链接，并编码 Markdown URL 分隔符。"""
    url = url.strip()
    try:
        parsed = urlsplit(url)
    except ValueError:
        return "#"
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return "#"
    return quote(url, safe=":/?#[]@!$&'*,;=%+~")


def render_markdown(items: list[ContentItem], date: datetime) -> str:
    """渲染 Markdown 简报:按分类分节,每条目含 title/score/summary/深层字段。

    示例:
        md = render_markdown(items, date=datetime.now())
    """
    date_str = date.strftime("%Y-%m-%d")

    lines: list[str] = []
    lines.append(f"# {_LABELS['title']} · {date_str}")
    lines.append("")

    if not items:
        lines.append(_LABELS["no_items"])
        return "\n".join(lines)

    # 统计
    lines.append(f"**{_LABELS['stats']}**: {len(items)} {_LABELS['items']}")
    lines.append("")

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
        lines.append(f"## {_plain_markdown_text(cat)}")
        lines.append("")

        for item in cat_items:
            _render_item(lines, item)
            lines.append("")

    return "\n".join(lines)


def _render_item(lines: list[str], item: ContentItem) -> None:
    """渲染单条目:标题 + 分数 + 摘要 + 标签。"""
    analysis = item.processing.analysis if item.processing and item.processing.analysis else None

    title = item.title or "Untitled"
    url = item.url or "#"
    score_str = f"{analysis.score:.1f}" if analysis and analysis.score is not None else "-"
    lines.append(f"### [{_escape_link_text(title)}]({_escape_link_url(url)})")
    lines.append("")
    lines.append(f"- **{_LABELS['score']}**: {score_str}")

    summary = analysis.summary if analysis else None
    if summary:
        lines.append(f"- **{_LABELS['summary']}**: {_plain_markdown_text(summary)}")

    if analysis and analysis.tags:
        tags = ", ".join(_plain_markdown_text(tag) for tag in analysis.tags)
        lines.append(f"- **{_LABELS['tags']}: {tags}**")
