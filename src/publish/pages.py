"""GitHub Pages 发布:写入 docs/_posts/YYYY-MM-DD.md,带 Jekyll front matter。

文件名格式遵循 Jekyll 约定:YYYY-MM-DD-slug.md,本系统 slug 省略(单语中文产物)。
front matter 含 layout/title/date。
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


class GitHubPagesPublisher:
    """GitHub Pages 发布器:写入 Jekyll 兼容的 Markdown 文件。

    示例:
        publisher = GitHubPagesPublisher("docs/_posts")
        publisher.publish(content=md, date=datetime.now())
    """

    def __init__(self, posts_dir: Path | str):
        """指定 docs/_posts 目录,不存在时延迟创建(首次 publish 时建)。"""
        self.posts_dir = Path(posts_dir)

    def publish(self, content: str, date: datetime) -> Path:
        """发布简报到 docs/_posts/YYYY-MM-DD.md,返回文件路径。

        文件含 Jekyll front matter(layout/title/date)。title 从内容首行 `#` 标题提取。
        """
        self.posts_dir.mkdir(parents=True, exist_ok=True)
        date_str = date.strftime("%Y-%m-%d")
        path = self.posts_dir / f"{date_str}.md"
        path.write_text(self._with_front_matter(content, date), encoding="utf-8")
        return path

    def _with_front_matter(self, content: str, date: datetime) -> str:
        """添加 Jekyll front matter:layout/title/date。"""
        first_line = content.lstrip().split("\n", 1)[0] if content.strip() else ""
        # 用正则去掉行首 # 与空白,避免 lstrip("# ") 按字符集误吃 "#hashtag" 中的 #
        title = re.sub(r"^#+\s*", "", first_line).strip() or f"每日简报 {date.strftime('%Y-%m-%d')}"
        date_iso = date.strftime("%Y-%m-%d")
        # title 用 YAML 双引号字符串,转义内部双引号防止破坏 front matter
        escaped_title = title.replace('"', '\\"')
        front_matter = (
            "---\n"
            "layout: post\n"
            f'title: "{escaped_title}"\n'
            f"date: {date_iso}\n"
            "---\n\n"
        )
        return front_matter + content
