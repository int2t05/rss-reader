"""Markdown 简报渲染:中文分类、新闻句链接与轻量日期信息。

渲染顺序:日期标题 → 统计 → 按分类分节 → 每分类下条目列表。
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Mapping
from datetime import datetime
from urllib.parse import quote, urlsplit

from src.models import ContentItem

# 简报各部分中文标签
_LABELS = {
    "title": "每日简报",
    "stats": "本期精选",
    "items": "条",
    "no_items": "今天没有精选内容。",
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


def render_markdown(
    items: list[ContentItem],
    date: datetime,
    period: str | None = None,
    category_labels: Mapping[str, str] | None = None,
) -> str:
    """渲染中文日报:分类名取配置显示名,新闻句作为链接标题。

    period 非空时标题用它(区间合刊,如 "2026-10-24 ~ 2026-11-02"),否则用单日日期。

    示例:
        md = render_markdown(items, date=datetime.now())
    """
    date_str = period or date.strftime("%Y-%m-%d")

    lines: list[str] = []
    lines.append(f"# {_LABELS['title']} · {date_str}")
    lines.append("")

    if not items:
        lines.append(_LABELS["no_items"])
        return "\n".join(lines)

    # 显示精选总数,不暴露内部排序分数。
    lines.append(f"**{_LABELS['stats']}**：{len(items)} {_LABELS['items']}")
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
        category_name = (category_labels or {}).get(cat, "其他" if cat == "unknown" else cat)
        category_id = f" {{#{cat}}}" if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", cat) else ""
        lines.append(f"## {_plain_markdown_text(category_name)}{category_id}")
        lines.append("")

        for item in cat_items:
            _render_item(lines, item)
            lines.append("")

    return "\n".join(lines)


def _render_item(lines: list[str], item: ContentItem) -> None:
    """渲染单条新闻:中文新闻句链接到原文,日期作为轻量补充信息。"""
    analysis = item.processing.analysis if item.processing and item.processing.analysis else None

    headline = (analysis.summary if analysis else "").strip() or item.title or "未命名条目"
    url = item.url or "#"
    lines.append(f"### [{_escape_link_text(headline)}]({_escape_link_url(url)})")
    lines.append("")
    lines.append(f"*发布于 {item.published_at.month}月{item.published_at.day}日*")
