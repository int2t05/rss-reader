"""CLI 入口:argparse 解析参数,分发到 --check-config / --fetch-only / --classify-only
/ --select-only / 完整 pipeline。

RSS feed 即消息队列(不按时间窗口过滤),DedupStore 即消费位点(断点续传),
每源每日消费上限由编排层控制。编排逻辑见 src/orchestrator.py。

示例:
    uv run rss-reader --check-config
    uv run rss-reader --fetch-only
    uv run rss-reader --classify-only --limit 10
    uv run rss-reader --select-only --limit 15
    uv run rss-reader --log-level DEBUG
    uv run rss-reader                                # 完整 pipeline(默认)
    uv run rss-reader --no-publish                   # 完整 pipeline,跳过发布
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

from src.orchestrator import (
    run_check_config,
    run_classify_only,
    run_fetch_only,
    run_pipeline,
    run_select_only,
)


def build_parser() -> argparse.ArgumentParser:
    """构建 CLI 参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="rss-reader",
        description="Personal information aggregation and AI summary system.",
    )
    parser.add_argument(
        "-d",
        "--project-dir",
        type=str,
        default=None,
        help="Path to project root (contains data/, categories/, feeds/)",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        default=None,
        help="Path to config file (overrides data/config.json)",
    )
    parser.add_argument(
        "-l",
        "--log-level",
        type=str,
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level",
    )
    parser.add_argument("--check-config", action="store_true", help="Validate config and exit")
    parser.add_argument("--fetch-only", action="store_true", help="Fetch sources only, skip AI analysis")
    parser.add_argument("--classify-only", action="store_true", help="Run Tier 1 classification only")
    parser.add_argument("--select-only", action="store_true", help="Run Tier 1 + Tier 2 selection")
    parser.add_argument("--no-publish", action="store_true", help="Skip publishing")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Backfill: produce briefing for YYYY-MM-DD (skip dedup, skip mark-processed)",
    )
    parser.add_argument("--limit", type=int, default=None, help="Limit items processed (for --classify-only)")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 入口:解析参数,分发到对应子命令。"""
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    # 静音 httpx/openai 每请求 INFO 日志,保留 WARNING+,避免淹没管线进度日志
    for noisy in ("httpx", "httpx2", "httpcore", "openai._base_client"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # 加载 .env(若存在),复用 Claude Code 凭证或用户自有 key
    load_dotenv(override=False)

    project_dir = Path(args.project_dir) if args.project_dir else None

    if args.check_config:
        return run_check_config(project_dir, args.config)

    if args.fetch_only:
        return asyncio.run(run_fetch_only(project_dir, args.config))

    if args.classify_only:
        return asyncio.run(run_classify_only(project_dir, args.limit, args.config))

    if args.select_only:
        return asyncio.run(run_select_only(project_dir, args.limit, args.config))

    # 默认:完整 pipeline
    date = _parse_date(args.date)
    return asyncio.run(run_pipeline(project_dir, args.no_publish, args.limit, args.config, date=date))


def _parse_date(s: str | None):
    """解析 --date YYYY-MM-DD 为 UTC datetime,返回 None 表示用当前时间。"""
    if s is None:
        return None
    return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=UTC)


if __name__ == "__main__":
    sys.exit(main())
