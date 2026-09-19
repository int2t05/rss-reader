"""GitHub Pages 发布测试:写入 docs/_posts/YYYY-MM-DD-daily-briefing.md,带 Jekyll front matter。

真实文件 I/O,无网络无 LLM。
"""
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.publish.pages import GitHubPagesPublisher


@pytest.fixture
def publisher(tmp_path: Path) -> GitHubPagesPublisher:
    """临时 docs/_posts 目录的 Publisher。"""
    return GitHubPagesPublisher(posts_dir=tmp_path / "docs" / "_posts")


def test_publisher_publish_creates_file(publisher: GitHubPagesPublisher):
    """发布简报:创建 YYYY-MM-DD-daily-briefing.md,含 Jekyll front matter。"""
    date = datetime(2026, 9, 17, tzinfo=timezone.utc)
    path = publisher.publish(content="# 中文简报", date=date)
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "中文简报" in content
    # Jekyll front matter
    assert content.startswith("---")
    assert "layout: post" in content
    assert "title:" in content
    assert "date:" in content


def test_publisher_creates_dir_if_not_exists(tmp_path: Path):
    """docs/_posts 不存在时自动创建。"""
    posts_dir = tmp_path / "new" / "docs" / "_posts"
    publisher = GitHubPagesPublisher(posts_dir=posts_dir)
    assert not posts_dir.exists()
    date = datetime(2026, 9, 17, tzinfo=timezone.utc)
    publisher.publish(content="# 简报", date=date)
    assert posts_dir.exists()
    assert (posts_dir / "2026-09-17-daily-briefing.md").exists()


def test_publisher_front_matter_contains_title(publisher: GitHubPagesPublisher):
    """Jekyll front matter 含 title 字段,从内容首行 # 标题提取。"""
    date = datetime(2026, 9, 17, tzinfo=timezone.utc)
    publisher.publish(content="# 简报标题", date=date)
    file_content = (publisher.posts_dir / "2026-09-17-daily-briefing.md").read_text(encoding="utf-8")
    # front matter 中应有 title
    assert "title:" in file_content.split("---")[1]
    assert "简报标题" in file_content.split("---")[1]


def test_publisher_overwrites_existing(publisher: GitHubPagesPublisher):
    """重复发布同一日期:覆盖旧内容。"""
    date = datetime(2026, 9, 17, tzinfo=timezone.utc)
    publisher.publish(content="旧简报", date=date)
    publisher.publish(content="新简报", date=date)
    file_content = (publisher.posts_dir / "2026-09-17-daily-briefing.md").read_text(encoding="utf-8")
    assert "新简报" in file_content
    assert "旧简报" not in file_content


def test_publisher_no_lang_in_front_matter(publisher: GitHubPagesPublisher):
    """front matter 不含 lang 字段(单语中文产物)。"""
    date = datetime(2026, 9, 17, tzinfo=timezone.utc)
    publisher.publish(content="# 简报", date=date)
    file_content = (publisher.posts_dir / "2026-09-17-daily-briefing.md").read_text(encoding="utf-8")
    front_matter = file_content.split("---")[1]
    assert "lang:" not in front_matter


def test_publisher_title_with_quotes_escaped(publisher: GitHubPagesPublisher):
    """title 含双引号时转义,不破坏 YAML front matter。"""
    date = datetime(2026, 9, 17, tzinfo=timezone.utc)
    publisher.publish(content='# "引号"标题', date=date)
    file_content = (publisher.posts_dir / "2026-09-17-daily-briefing.md").read_text(encoding="utf-8")
    front_matter = file_content.split("---")[1]
    # 转义后的双引号应出现在 title 行
    assert 'title: "\\"引号\\"标题"' in front_matter


def test_publisher_hashtag_title_not_stripped(publisher: GitHubPagesPublisher):
    """标题首行 # 后紧贴非空白字符(如 #hashtag)时,lstrip 误吃 # 已修复。"""
    date = datetime(2026, 9, 17, tzinfo=timezone.utc)
    publisher.publish(content="#hashtag 标题", date=date)
    file_content = (publisher.posts_dir / "2026-09-17-daily-briefing.md").read_text(encoding="utf-8")
    front_matter = file_content.split("---")[1]
    # #hashtag 的 # 不应被吃掉
    assert "hashtag" in front_matter
