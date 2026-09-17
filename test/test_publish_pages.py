"""GitHub Pages 发布测试:写入 docs/_posts/YYYY-MM-DD-{zh,en}.md,带 Jekyll front matter。

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


def test_publisher_publish_zh_creates_file(publisher: GitHubPagesPublisher):
    """发布中文简报:创建 YYYY-MM-DD-zh.md,含 Jekyll front matter。"""
    date = datetime(2026, 9, 17, tzinfo=timezone.utc)
    paths = publisher.publish(zh="# 中文简报", en="# English", date=date)
    zh_path = paths[0]
    assert zh_path.exists()
    content = zh_path.read_text(encoding="utf-8")
    assert "中文简报" in content
    # Jekyll front matter
    assert content.startswith("---")
    assert "layout: post" in content
    assert "title:" in content
    assert "date:" in content


def test_publisher_publish_en_creates_file(publisher: GitHubPagesPublisher):
    """发布英文简报:创建 YYYY-MM-DD-en.md。"""
    date = datetime(2026, 9, 17, tzinfo=timezone.utc)
    paths = publisher.publish(zh="# 中文", en="# English Briefing", date=date)
    en_path = paths[1]
    assert en_path.exists()
    content = en_path.read_text(encoding="utf-8")
    assert "English Briefing" in content


def test_publisher_publish_both_creates_two_files(publisher: GitHubPagesPublisher):
    """发布双语:创建两个文件。"""
    date = datetime(2026, 9, 17, tzinfo=timezone.utc)
    paths = publisher.publish(zh="# 中文", en="# English", date=date)
    assert len(paths) == 2
    assert paths[0].name == "2026-09-17-zh.md"
    assert paths[1].name == "2026-09-17-en.md"


def test_publisher_creates_dir_if_not_exists(tmp_path: Path):
    """docs/_posts 不存在时自动创建。"""
    posts_dir = tmp_path / "new" / "docs" / "_posts"
    publisher = GitHubPagesPublisher(posts_dir=posts_dir)
    assert not posts_dir.exists()
    date = datetime(2026, 9, 17, tzinfo=timezone.utc)
    publisher.publish(zh="# 简报", en="# Briefing", date=date)
    assert posts_dir.exists()
    assert (posts_dir / "2026-09-17-zh.md").exists()


def test_publisher_front_matter_contains_title(publisher: GitHubPagesPublisher):
    """Jekyll front matter 含 title 字段。"""
    date = datetime(2026, 9, 17, tzinfo=timezone.utc)
    publisher.publish(zh="# 简报标题", en="# Briefing Title", date=date)
    zh_content = (publisher.posts_dir / "2026-09-17-zh.md").read_text(encoding="utf-8")
    # front matter 中应有 title
    assert "title:" in zh_content.split("---")[1]


def test_publisher_overwrites_existing(publisher: GitHubPagesPublisher):
    """重复发布同一日期:覆盖旧内容。"""
    date = datetime(2026, 9, 17, tzinfo=timezone.utc)
    publisher.publish(zh="旧简报", en="old", date=date)
    publisher.publish(zh="新简报", en="new", date=date)
    zh_content = (publisher.posts_dir / "2026-09-17-zh.md").read_text(encoding="utf-8")
    assert "新简报" in zh_content
    assert "旧简报" not in zh_content


def test_publisher_front_matter_contains_lang(publisher: GitHubPagesPublisher):
    """Jekyll front matter 含 lang 字段(zh/en)。"""
    date = datetime(2026, 9, 17, tzinfo=timezone.utc)
    publisher.publish(zh="# 中文", en="# English", date=date)
    zh_content = (publisher.posts_dir / "2026-09-17-zh.md").read_text(encoding="utf-8")
    en_content = (publisher.posts_dir / "2026-09-17-en.md").read_text(encoding="utf-8")
    assert "lang: zh" in zh_content
    assert "lang: en" in en_content
