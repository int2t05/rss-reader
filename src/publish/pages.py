"""GitHub Pages 发布:写入 docs/_posts/YYYY-MM-DD-{zh,en}.md,带 Jekyll front matter。

文件名格式遵循 Jekyll 约定:YYYY-MM-DD-{slug}.md。front matter 含 layout/title/date/lang。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


class GitHubPagesPublisher:
    """GitHub Pages 发布器:写入 Jekyll 兼容的 Markdown 文件。

    示例:
        publisher = GitHubPagesPublisher("docs/_posts")
        publisher.publish(zh=zh_md, en=en_md, date=datetime.now())
    """

    def __init__(self, posts_dir: Path | str):
        """指定 docs/_posts 目录,不存在时延迟创建(首次 publish 时建)。"""
        self.posts_dir = Path(posts_dir)

    def publish(self, zh: str, en: str, date: datetime) -> tuple[Path, Path]:
        """发布中英两份简报到 docs/_posts/YYYY-MM-DD-{zh,en}.md,返回两文件路径。

        每份文件含 Jekyll front matter(layout/title/date/lang)。
        """
        self.posts_dir.mkdir(parents=True, exist_ok=True)
        date_str = date.strftime("%Y-%m-%d")
        zh_path = self.posts_dir / f"{date_str}-zh.md"
        en_path = self.posts_dir / f"{date_str}-en.md"
        zh_path.write_text(self._with_front_matter(zh, date, lang="zh"), encoding="utf-8")
        en_path.write_text(self._with_front_matter(en, date, lang="en"), encoding="utf-8")
        return zh_path, en_path

    def _with_front_matter(self, content: str, date: datetime, lang: str) -> str:
        """添加 Jekyll front matter:layout/title/date/lang。"""
        # 从内容首行提取标题(若有 # 开头)
        first_line = content.lstrip().split("\n", 1)[0] if content.strip() else ""
        # TODO: lstrip("# ") 按字符集剥离,会吃掉 "#hashtag" 中的 #,应改用 removeprefix("# ") 或 re.sub(r'^#+\s*','')
        title = first_line.lstrip("# ").strip() or f"Daily Briefing {date.strftime('%Y-%m-%d')} ({lang})"
        date_iso = date.strftime("%Y-%m-%d")
        # TODO: title 含双引号会破坏 YAML front matter,应转义或用 block scalar
        front_matter = (
            "---\n"
            f"layout: post\n"
            f'title: "{title}"\n'
            f"date: {date_iso}\n"
            f"lang: {lang}\n"
            "---\n\n"
        )
        return front_matter + content
