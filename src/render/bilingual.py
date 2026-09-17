"""双语渲染:同一份源数据渲染中英两份 Markdown 简报。

返回 BilingualResult(zh, en),供 Pages 发布到 docs/_posts/YYYY-MM-DD-{zh,en}.md。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.models import ContentItem
from src.render.markdown import render_markdown


@dataclass
class BilingualResult:
    """双语渲染结果:zh + en 两份 Markdown 字符串。"""

    zh: str
    en: str


def render_bilingual(items: list[ContentItem], date: datetime) -> BilingualResult:
    """同一份源数据渲染中英两份 Markdown 简报。

    示例:
        result = render_bilingual(items, date=datetime.now())
        # result.zh 是中文简报,result.en 是英文简报
    """
    zh = render_markdown(items, date=date, lang="zh")
    en = render_markdown(items, date=date, lang="en")
    return BilingualResult(zh=zh, en=en)
