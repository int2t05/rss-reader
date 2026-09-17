"""总结落盘:Markdown 写入 data/summaries/YYYY-MM-DD[-(zh|en)].md。

支持单语与双语保存,可列出已保存日期。目录不存在时自动创建。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


class SummaryStore:
    """Markdown 总结存储:落盘到 data/summaries/ 目录,可 diff,可 git。

    示例:
        store = SummaryStore("data/summaries")
        store.save_bilingual(zh=zh_md, en=en_md, date=datetime.now())
    """

    def __init__(self, summaries_dir: Path | str):
        """指定 summaries 目录,不存在时延迟创建(首次 save 时建)。"""
        self.summaries_dir = Path(summaries_dir)

    def summary_path(self, date: datetime, lang: str | None = None) -> Path:
        """返回总结文件路径:YYYY-MM-DD.md 或 YYYY-MM-DD-{lang}.md。"""
        date_str = date.strftime("%Y-%m-%d")
        if lang:
            return self.summaries_dir / f"{date_str}-{lang}.md"
        return self.summaries_dir / f"{date_str}.md"

    def save(self, content: str, date: datetime) -> Path:
        """写入单语总结到 data/summaries/YYYY-MM-DD.md,返回文件路径。"""
        self.summaries_dir.mkdir(parents=True, exist_ok=True)
        path = self.summary_path(date)
        path.write_text(content, encoding="utf-8")
        return path

    def save_bilingual(self, zh: str, en: str, date: datetime) -> tuple[Path, Path]:
        """写入中英两份总结:YYYY-MM-DD-zh.md + YYYY-MM-DD-en.md。"""
        self.summaries_dir.mkdir(parents=True, exist_ok=True)
        zh_path = self.summary_path(date, lang="zh")
        en_path = self.summary_path(date, lang="en")
        zh_path.write_text(zh, encoding="utf-8")
        en_path.write_text(en, encoding="utf-8")
        return zh_path, en_path

    def load(self, date: datetime, lang: str | None = None) -> str | None:
        """加载指定日期总结,不存在返回 None。"""
        path = self.summary_path(date, lang=lang)
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def list_summaries(self) -> list[datetime]:
        """列出已保存总结日期(按日期降序),仅扫描单语 YYYY-MM-DD.md。"""
        if not self.summaries_dir.exists():
            return []
        dates: list[datetime] = []
        for p in self.summaries_dir.glob("*.md"):
            # 仅 YYYY-MM-DD.md(无 -zh/-en 后缀)
            name = p.stem
            if "-" in name and name.count("-") == 2 and len(name) == 10:
                try:
                    dates.append(datetime.strptime(name, "%Y-%m-%d"))
                except ValueError:
                    continue
        dates.sort(reverse=True)
        return dates
