"""RSS 源抓取器:httpx 抓 feed → feedparser 解析 → 日期过滤 → ContentItem 列表。

借鉴 Horizon src/scrapers/rss.py:日期解析带时区回退,环境变量展开。
"""

from __future__ import annotations

import calendar
import hashlib
import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import httpx

from src.models import ContentItem, RSSSourceConfig, SourceType
from src.utils.env import expand_env

logger = logging.getLogger(__name__)


class RSSSource:
    """RSS/Atom 源:配置驱动,用 feedparser 解析,支持 ${VAR} 环境变量展开。"""

    # 每源条目上限:截断高产出源(如 arXiv 子类每日数百篇),控制 Tier1 成本与时延
    _MAX_ITEMS_PER_SOURCE = 30

    def __init__(self, config: RSSSourceConfig, http_client: httpx.AsyncClient):
        self.config = config
        self.client = http_client

    @property
    def category(self) -> str:
        """源归入的分类路径(如 "ai-research/ai-vendor")。"""
        return self.config.category

    async def fetch(self, since: datetime) -> list[ContentItem]:
        """抓取 since 之后的新条目,每源截断至最近 _MAX_ITEMS_PER_SOURCE 条。单源失败返回空列表。"""
        items: list[ContentItem] = []
        try:
            feed_url = expand_env(self.config.url)
            response = await self.client.get(feed_url, follow_redirects=True)
            response.raise_for_status()

            feed = feedparser.parse(response.text)
            for entry in feed.entries:
                published_at = self._parse_date(entry)
                if not published_at or published_at < since:
                    continue

                item = ContentItem(
                    id=self._generate_id(entry),
                    source_type=SourceType.RSS,
                    title=entry.get("title", "Untitled"),
                    url=entry.get("link", self.config.url),
                    content=self._extract_content(entry),
                    author=entry.get("author", self.config.name),
                    published_at=published_at,
                    category=self.config.category,  # 源级 category hint
                    metadata={
                        "feed_name": self.config.name,
                        "category": self.config.category,
                        "tags": [tag.term for tag in entry.get("tags", []) or []],
                    },
                )
                items.append(item)
        except httpx.HTTPError as e:
            logger.warning("HTTP error fetching RSS %s: %s", self.config.name, e)
        except Exception as e:
            logger.warning("Error parsing RSS %s: %s", self.config.name, e)
        # 截断高产出源(arXiv 子类等),保留最近 N 条(entries 通常已按时间倒序)
        return items[: self._MAX_ITEMS_PER_SOURCE]

    def _parse_date(self, entry: dict) -> datetime | None:
        """解析发布日期,优先 struct_time,回退 RFC2822,无时区补 UTC。

        借鉴 Horizon:published_parsed → updated_parsed → created_parsed。
        """
        for field in ("published", "updated", "created"):
            if field not in entry:
                continue
            try:
                parsed_field = f"{field}_parsed"
                if entry.get(parsed_field):
                    return datetime.fromtimestamp(
                        calendar.timegm(entry[parsed_field]), tz=timezone.utc
                    )
                date_str = entry[field]
                if not isinstance(date_str, str):
                    continue
                parsed = parsedate_to_datetime(date_str)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed
            except Exception:
                continue
        return None

    def _extract_content(self, entry: dict) -> str:
        """提取正文:summary → description → content[0].value。"""
        if "summary" in entry:
            return entry.summary or ""
        if "description" in entry:
            return entry.description or ""
        if "content" in entry and entry.content:
            return entry.content[0].get("value", "") or ""
        return ""

    def _generate_id(self, entry: dict) -> str:
        """生成稳定唯一 ID:源名 slug + entry 标识(id/link,回退 title+发布时间+正文)哈希。

        源名作前缀不受 RSSHub base_url 变更影响;id/link 缺失时回退内容指纹避免碰撞。
        """
        entry_id = entry.get("id") or entry.get("link") or ""
        if not entry_id:
            # id/link 都缺失时,用 title + 发布时间 + 正文前缀生成稳定标识,避免多条目碰撞
            title = entry.get("title", "")
            published = entry.get("published", entry.get("updated", ""))
            content_prefix = (self._extract_content(entry) or "")[:200]
            entry_id = f"{title}|{published}|{content_prefix}"
        entry_hash = hashlib.sha256(entry_id.encode("utf-8")).hexdigest()[:16]
        source_slug = re.sub(r"[^\w]", "_", self.config.name) or "source"
        return f"rss_{source_slug}_{entry_hash}"
