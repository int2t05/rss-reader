"""总结落盘:Markdown 写入 data/summaries/YYYY-MM-DD.md。

目录不存在时自动创建。可列出已保存日期。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


class SummaryStore:
    """Markdown 总结存储:落盘到 data/summaries/ 目录,可 diff,可 git。

    示例:
        store = SummaryStore("data/summaries")
        store.save(content=md, date=datetime.now())
    """

    def __init__(self, summaries_dir: Path | str):
        """指定 summaries 目录,不存在时延迟创建(首次 save 时建)。"""
        self.summaries_dir = Path(summaries_dir)

    def summary_path(self, date: datetime) -> Path:
        """返回总结文件路径:YYYY-MM-DD.md。"""
        date_str = date.strftime("%Y-%m-%d")
        return self.summaries_dir / f"{date_str}.md"

    def save(self, content: str, date: datetime) -> Path:
        """写入总结到 data/summaries/YYYY-MM-DD.md,返回文件路径。"""
        self.summaries_dir.mkdir(parents=True, exist_ok=True)
        path = self.summary_path(date)
        path.write_text(content, encoding="utf-8")
        return path

    def load(self, date: datetime) -> str | None:
        """加载指定日期总结,不存在返回 None。"""
        path = self.summary_path(date)
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def list_summaries(self) -> list[datetime]:
        """列出已保存总结日期(按日期降序),扫描 YYYY-MM-DD.md。"""
        if not self.summaries_dir.exists():
            return []
        dates: list[datetime] = []
        for p in self.summaries_dir.glob("*.md"):
            name = p.stem
            if name.count("-") == 2 and len(name) == 10:
                try:
                    dates.append(datetime.strptime(name, "%Y-%m-%d"))
                except ValueError:
                    continue
        dates.sort(reverse=True)
        return dates
