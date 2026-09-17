"""RSS 源抓取器:httpx 抓 feed → feedparser 解析 → 日期过滤 → ContentItem 列表。

借鉴 Horizon src/scrapers/rss.py:日期解析带时区回退,环境变量展开。
"""

from __future__ import annotations

import calendar
import hashlib
import logging
import os
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import httpx

from src.models import ContentItem, RSSSourceConfig, SourceType

logger = logging.getLogger(__name__)

_ENV_VAR_PATTERN = re.compile(r"\$\{(\w+)\}")


def _expand_env(value: str) -> str:
    """将 ${VAR_NAME} 替换为 os.environ['VAR_NAME'],未定义时保留原样。

    示例:"http://host/feed/${TOKEN}" → "http://host/feed/secret-123"
    """
    return _ENV_VAR_PATTERN.sub(
        lambda m: os.environ.get(m.group(1), m.group(0)).strip(),
        value,
    )


class RSSSource:
    """RSS/Atom 源:配置驱动,用 feedparser 解析,支持 ${VAR} 环境变量展开。"""

    def __init__(self, config: RSSSourceConfig, http_client: httpx.AsyncClient):
        self.config = config
        self.client = http_client

    @property
    def category(self) -> str:
        """源归入的分类路径(如 "ai-research/ai-vendor")。"""
        return self.config.category

    async def fetch(self, since: datetime) -> list[ContentItem]:
        """抓取 since 之后的新条目。单源失败返回空列表,不抛异常。"""
        items: list[ContentItem] = []
        try:
            feed_url = _expand_env(self.config.url)
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
                        # TODO: entry.get("tags", []) 对 None 不安全,tags=None 时抛 TypeError 跳过整源
                        "tags": [tag.term for tag in entry.get("tags", []) or []],
                    },
                )
                items.append(item)
        except httpx.HTTPError as e:
            logger.warning("HTTP error fetching RSS %s: %s", self.config.name, e)
        except Exception as e:
            logger.warning("Error parsing RSS %s: %s", self.config.name, e)
        return items

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
        """生成稳定唯一 ID:feed_url 哈希 + entry id 哈希。"""
        # TODO: id/link 都缺失时 entry_id="",产生固定哈希,多条目碰撞丢数据
        entry_id = entry.get("id", entry.get("link", ""))
        entry_hash = hashlib.sha256(str(entry_id).encode("utf-8")).hexdigest()[:16]
        # TODO: feed_id 提取脆弱,localhost:5000 含冒号,RSSHub base_url 变更导致去重失效
        feed_id = str(self.config.url).split("//")[-1].replace("/", "_")
        return f"rss_{feed_id}_{entry_hash}"
