"""GitHub Pages 发布:写入 docs/_posts/YYYY-MM-DD-daily-briefing.md,带 Chirpy 兼容 front matter。

文件名格式遵循 Jekyll 约定:YYYY-MM-DD-slug.md(Chirpy 要求带 slug,否则不识别为 post)。
front matter 含 layout/title/date(带时区)/categories/tags,适配 Chirpy 主题。
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

# Jekyll post 文件名 slug(固定,日报无独立标题)
_POST_SLUG = "daily-briefing"


class GitHubPagesPublisher:
    """GitHub Pages 发布器:写入 Chirpy 兼容的 Markdown 文件。

    示例:
        publisher = GitHubPagesPublisher("docs/_posts")
        publisher.publish(content=md, date=datetime.now())
    """

    def __init__(self, posts_dir: Path | str):
        """指定 docs/_posts 目录,不存在时延迟创建(首次 publish 时建)。"""
        self.posts_dir = Path(posts_dir)

    def publish(self, content: str, date: datetime) -> Path:
        """发布简报到 docs/_posts/YYYY-MM-DD-daily-briefing.md,返回文件路径。

        文件含 Chirpy 兼容 front matter(layout/title/date/categories/tags)。
        title 从内容首行 `#` 标题提取;tags 从正文 `## 分类` 节提取(全小写)。
        """
        self.posts_dir.mkdir(parents=True, exist_ok=True)
        date_str = date.strftime("%Y-%m-%d")
        path = self.posts_dir / f"{date_str}-{_POST_SLUG}.md"
        path.write_text(self._with_front_matter(content, date), encoding="utf-8")
        return path

    def _with_front_matter(self, content: str, date: datetime) -> str:
        """添加 Chirpy 兼容 front matter:layout/title/date/categories/tags。

        date 带时区(+0800)满足 Chirpy 要求;tags 从正文 ## 分类节提取,全小写。
        """
        first_line = content.lstrip().split("\n", 1)[0] if content.strip() else ""
        # 用正则去掉行首 # 与空白,避免 lstrip("# ") 按字符集误吃 "#hashtag" 中的 #
        title = re.sub(r"^#+\s*", "", first_line).strip() or f"每日简报 {date.strftime('%Y-%m-%d')}"
        # Chirpy 要求 date 带时分和时区偏移,如 2026-09-18 09:00:00 +0800
        date_chirpy = date.strftime("%Y-%m-%d %H:%M:%S +0800")
        # title 用 YAML 双引号字符串,转义内部双引号防止破坏 front matter
        escaped_title = title.replace('"', '\\"')
        # tags 从正文 ## 分类节提取(如 ## ai-research → ai-research),全小写
        tags = self._extract_tags(content)
        tags_yaml = ", ".join(tags) if tags else "日报"
        front_matter = (
            "---\n"
            "layout: post\n"
            f'title: "{escaped_title}"\n'
            f"date: {date_chirpy}\n"
            "categories: [简报]\n"
            f"tags: [{tags_yaml}]\n"
            "---\n\n"
        )
        return front_matter + content

    def _extract_tags(self, content: str) -> list[str]:
        """从正文 ## 分类节标题提取标签(如 ## ai-research → ai-research),全小写。"""
        return [
            m.lower()
            for m in re.findall(r"^##\s+(\S+)", content, re.MULTILINE)
            if not m.startswith("#")
        ]
