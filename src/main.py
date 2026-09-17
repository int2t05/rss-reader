"""CLI 入口:argparse 解析参数,分发到 --check-config / --fetch-only / --classify-only / --select-only / --analyze-one / 完整 pipeline。

示例:
    uv run rss-reader --check-config
    uv run rss-reader --fetch-only --hours 24
    uv run rss-reader --classify-only --hours 24 --limit 10
    uv run rss-reader --select-only --hours 24 --limit 15
    uv run rss-reader --analyze-one <item_id> --hours 24
    uv run rss-reader --hours 24 --log-level DEBUG
    uv run rss-reader --hours 24                       # 完整 pipeline(默认)
    uv run rss-reader --hours 24 --no-publish          # 完整 pipeline,跳过发布
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from src.ai.agent.crag import CRAGEvaluator
from src.ai.agent.fetch_chain import FetchChain
from src.ai.agent.loop import AgentLoop
from src.ai.agent.search_chain import SearchChain
from src.ai.agent.tool import ToolRegistry
from src.ai.classifier import ContentClassifier
from src.ai.client import AIClient, AIClientConfig
from src.ai.selector import ContentSelector
from src.config import Config, load_config
from src.processing.categories import CategoryRegistry
from src.publish.pages import GitHubPagesPublisher
from src.publish.webhook import WebhookPublisher
from src.render.bilingual import render_bilingual
from src.sources.registry import SourceRegistry
from src.sources.rsshub import build_source
from src.storage.summaries import SummaryStore

logger = logging.getLogger(__name__)
console = Console()  # 结果输出走 stdout,便于管道
err_console = Console(stderr=True)  # 进度/告警走 stderr


def build_parser() -> argparse.ArgumentParser:
    """构建 CLI 参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="rss-reader",
        description="Personal information aggregation and AI summary system.",
    )
    parser.add_argument("--hours", type=int, default=24, help="Fetch from last N hours (default: 24)")
    parser.add_argument("-d", "--data-dir", type=str, default=None, help="Path to the data directory")
    parser.add_argument("-c", "--config", type=str, default=None, help="Path to config file")
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
    parser.add_argument("--analyze-one", type=str, default=None, help="Analyze a single item by ID")
    parser.add_argument("--no-publish", action="store_true", help="Skip publishing")
    parser.add_argument("--limit", type=int, default=None, help="Limit items processed (for --classify-only)")
    return parser


def run_check_config(project_dir: Path | None) -> int:
    """--check-config:加载配置,输出源数量与分类列表,返回退出码。"""
    try:
        cfg = load_config(project_dir)
    except FileNotFoundError as e:
        err_console.print(f"[red]Config error:[/red] {e}")
        return 1

    table = Table(title="rss-reader config")
    table.add_column("Category", style="cyan")
    table.add_column("Enabled", style="green")
    table.add_column("Threshold", style="yellow")
    table.add_column("Digest Limit", style="magenta")
    table.add_column("Children", style="blue")

    for cat in cfg.category_configs:
        table.add_row(
            cat.name,
            "yes" if cat.enabled else "no",
            str(cat.threshold),
            str(cat.digest_limit),
            ", ".join(cat.children) if cat.children else "-",
        )

    console.print(table)
    console.print(f"\n[bold]Sources:[/bold] {len(cfg.sources)} enabled")
    console.print(f"[bold]RSSHub base URL:[/bold] {cfg.rsshub_base_url or '(disabled)'}")
    return 0


def _build_registry(cfg, http_client: httpx.AsyncClient) -> SourceRegistry:
    """从配置构建 SourceRegistry:RSSHub 路由源根据 rsshub_base_url 决定跳过或解析。"""
    registry = SourceRegistry()
    for src_cfg in cfg.sources:
        source = build_source(src_cfg, cfg.rsshub_base_url, http_client)
        if source is not None:
            registry.register(source)
    return registry


async def run_fetch_only(project_dir: Path | None, hours: int) -> int:
    """--fetch-only:并发抓取所有源,输出每源条目数与总数,返回退出码。"""
    try:
        cfg = load_config(project_dir)
    except FileNotFoundError as e:
        err_console.print(f"[red]Config error:[/red] {e}")
        return 1

    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    total = 0
    async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
        registry = _build_registry(cfg, client)
        if len(registry) == 0:
            err_console.print("[yellow]No enabled sources.[/yellow]")
            return 0

        per_source: list[tuple[str, int]] = []
        for source in registry.all():
            try:
                items = await source.fetch(since)
                per_source.append((source.config.name if hasattr(source, "config") else source.category, len(items)))
                total += len(items)
            except Exception as e:
                logger.warning("Source %s failed: %s", source.category, e)
                per_source.append((source.category, 0))

    table = Table(title=f"Fetched in last {hours}h")
    table.add_column("Source", style="cyan")
    table.add_column("Items", style="green", justify="right")
    for name, count in per_source:
        table.add_row(name, str(count))
    table.add_row("[bold]Total[/bold]", f"[bold]{total}[/bold]")
    console.print(table)
    return 0


async def _fetch_all_items(cfg: Config, hours: int) -> list:
    """抓取所有源,返回合并后的 ContentItem 列表。"""
    # TODO: 当前为顺序抓取,70+ 源总耗时为各源之和;应改为 asyncio.gather 并发(单源失败不中断)
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    all_items = []
    async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
        registry = _build_registry(cfg, client)
        for source in registry.all():
            try:
                items = await source.fetch(since)
                all_items.extend(items)
            except Exception as e:
                logger.warning("Source %s failed: %s", source.category, e)
    return all_items


def _build_ai_client(cfg: Config) -> AIClient:
    """从配置构造 AIClient,OPENAI_MODEL 环境变量覆盖 config 中的 model。"""
    ai_cfg = cfg.ai
    model = os.environ.get("OPENAI_MODEL", ai_cfg.get("model", "gpt-4o-mini"))
    base_url = ai_cfg.get("base_url") or os.environ.get("OPENAI_BASE_URL")
    client_cfg = AIClientConfig(
        provider=ai_cfg.get("provider", "openai"),
        model=model,
        api_key_env=ai_cfg.get("api_key_env", "OPENAI_API_KEY"),
        base_url=base_url,
        analysis_concurrency=ai_cfg.get("analysis_concurrency", 5),
        throttle_sec=ai_cfg.get("throttle_sec", 0.0),
    )
    return AIClient(client_cfg)


def _build_category_registry(cfg: Config, project_dir: Path | None) -> CategoryRegistry:
    """从配置构造 CategoryRegistry,加载 enabled 分类。"""
    categories_root = (project_dir or Path.cwd()) / "categories"
    reg = CategoryRegistry(categories_root)
    reg.load_from_raw(cfg.categories)
    return reg


async def run_classify_only(project_dir: Path | None, hours: int, limit: int | None) -> int:
    """--classify-only:抓取 → Tier1 分类+打分,输出结果表格。"""
    try:
        cfg = load_config(project_dir)
    except FileNotFoundError as e:
        err_console.print(f"[red]Config error:[/red] {e}")
        return 1

    items = await _fetch_all_items(cfg, hours)
    if not items:
        err_console.print("[yellow]No items fetched.[/yellow]")
        return 0

    if limit:
        items = items[:limit]

    client = _build_ai_client(cfg)
    registry = _build_category_registry(cfg, project_dir)
    classifier = ContentClassifier(client, registry)

    err_console.print(f"[bold]Classifying {len(items)} items...[/bold]")
    items = await classifier.classify_batch(items)

    table = Table(title=f"Tier 1 Classification ({len(items)} items)")
    table.add_column("Title", style="cyan", max_width=40)
    table.add_column("Category", style="blue")
    table.add_column("Score", style="yellow", justify="right")
    table.add_column("Summary", style="green", max_width=50)
    for item in items:
        analysis = item.processing.analysis if item.processing and item.processing.analysis else None
        table.add_row(
            item.title[:40],
            analysis.category_path if analysis else "-",
            f"{analysis.score:.1f}" if analysis and analysis.score else "-",
            (analysis.summary[:50] if analysis and analysis.summary else "-"),
        )
    console.print(table)
    return 0


async def run_select_only(project_dir: Path | None, hours: int, limit: int | None) -> int:
    """--select-only:抓取 → Tier1 分类+打分 → Tier2 选取+去重,输出精选结果表格。"""
    try:
        cfg = load_config(project_dir)
    except FileNotFoundError as e:
        err_console.print(f"[red]Config error:[/red] {e}")
        return 1

    items = await _fetch_all_items(cfg, hours)
    if not items:
        err_console.print("[yellow]No items fetched.[/yellow]")
        return 0

    if limit:
        items = items[:limit]

    client = _build_ai_client(cfg)
    registry = _build_category_registry(cfg, project_dir)
    classifier = ContentClassifier(client, registry)
    selector = ContentSelector(registry, client=client)

    err_console.print(f"[bold]Classifying {len(items)} items...[/bold]")
    items = await classifier.classify_batch(items)

    err_console.print(f"[bold]Selecting from {len(items)} classified items...[/bold]")
    selected = await selector.select(items, use_llm_dedup=True)

    # 按分类分组输出
    grouped: dict[str, list] = {}
    for item in selected:
        path = item.processing.analysis.category_path if item.processing and item.processing.analysis else "unknown"
        grouped.setdefault(path, []).append(item)

    table = Table(title=f"Tier 2 Selection ({len(selected)} items)")
    table.add_column("Category", style="blue", max_width=25)
    table.add_column("Title", style="cyan", max_width=40)
    table.add_column("Score", style="yellow", justify="right")
    table.add_column("Summary", style="green", max_width=40)
    for cat_path in sorted(grouped.keys()):
        for item in grouped[cat_path]:
            analysis = item.processing.analysis if item.processing and item.processing.analysis else None
            table.add_row(
                cat_path,
                item.title[:40],
                f"{analysis.score:.1f}" if analysis and analysis.score else "-",
                (analysis.summary[:40] if analysis and analysis.summary else "-"),
            )
    console.print(table)
    console.print(f"\n[bold]Selected:[/bold] {len(selected)} / {len(items)} items")
    return 0


async def run_analyze_one(project_dir: Path | None, hours: int, item_id: str) -> int:
    """--analyze-one:抓取 → Tier1 → Tier2 → 对指定 item_id 跑 Tier3 agent 循环,输出深度分析。"""
    try:
        cfg = load_config(project_dir)
    except FileNotFoundError as e:
        err_console.print(f"[red]Config error:[/red] {e}")
        return 1

    items = await _fetch_all_items(cfg, hours)
    if not items:
        err_console.print("[yellow]No items fetched.[/yellow]")
        return 0

    client = _build_ai_client(cfg)
    registry = _build_category_registry(cfg, project_dir)
    classifier = ContentClassifier(client, registry)
    selector = ContentSelector(registry, client=client)

    err_console.print(f"[bold]Classifying {len(items)} items...[/bold]")
    items = await classifier.classify_batch(items)
    selected = await selector.select(items, use_llm_dedup=True)

    # 找到目标 item(先在 selected 中找,再在 items 中找)
    target = next((it for it in selected if it.id == item_id), None)
    if target is None:
        target = next((it for it in items if it.id == item_id), None)
    if target is None:
        # 模糊匹配:item_id 是前缀
        target = next((it for it in items if it.id.startswith(item_id) or item_id in it.id), None)
    if target is None:
        err_console.print(f"[red]Item not found:[/red] {item_id}")
        err_console.print(f"[dim]Available IDs (first 5):[/dim]")
        for it in items[:5]:
            err_console.print(f"  {it.id}  {it.title[:50]}")
        return 1

    err_console.print(f"[bold]Analyzing item:[/bold] {target.id} - {target.title}")
    err_console.print(f"[dim]CRAG verdict: computing...[/dim]")

    # 构造 AgentLoop
    crag = CRAGEvaluator()
    tool_registry = ToolRegistry()
    loop = AgentLoop(
        client=client,
        registry=tool_registry,
        crag=crag,
        search_chain=SearchChain.build_default(exa_api_key=os.environ.get("EXA_API_KEY")),
        fetch_chain=FetchChain.build_default(firecrawl_api_key=os.environ.get("FIRECRAWL_API_KEY")),
        max_steps=10,
    )

    # 获取分类 display_name
    cat = registry.get_by_path(target.category or "")
    display_name = cat.display_name.get("zh", cat.name) if cat else (target.category or "未知")

    result = await loop.run(target, category_display_name=display_name)

    # 输出深度分析结果
    console.print(f"\n[bold cyan]深度分析结果[/bold cyan]")
    console.print(f"[bold]标题:[/bold] {result.title}")
    console.print(f"[bold]分类:[/bold] {target.category or '-'}")
    console.print(f"\n[bold]摘要:[/bold]\n{result.summary}")
    if result.background:
        console.print(f"\n[bold]背景:[/bold]\n{result.background}")
    if result.impact:
        console.print(f"\n[bold]影响:[/bold]\n{result.impact}")
    if result.references:
        console.print(f"\n[bold]参考:[/bold]")
        for ref in result.references:
            console.print(f"  - {ref.title}: {ref.url}")
    if result.tags:
        console.print(f"\n[bold]标签:[/bold] {', '.join(result.tags)}")
    return 0


async def run_pipeline(project_dir: Path | None, hours: int, no_publish: bool, limit: int | None) -> int:
    """完整三段式 pipeline:抓取 → Tier1 分类+打分 → Tier2 选取+去重 → Tier3 agent 深度分析 → 双语渲染 → 落盘 + 发布。

    --no-publish 跳过发布,仅落盘到 data/summaries/。
    """
    # TODO: 编排逻辑内联在 CLI 入口,应抽取到 src/orchestrator.py(CLAUDE.md 结构声明),便于测试与复用
    try:
        cfg = load_config(project_dir)
    except FileNotFoundError as e:
        err_console.print(f"[red]Config error:[/red] {e}")
        return 1

    items = await _fetch_all_items(cfg, hours)
    if not items:
        err_console.print("[yellow]No items fetched.[/yellow]")
        return 0

    if limit:
        # 仅用于限制处理量(避免完整 pipeline 跑过多),默认不截断
        items = items[:limit]

    client = _build_ai_client(cfg)
    registry = _build_category_registry(cfg, project_dir)
    classifier = ContentClassifier(client, registry)
    selector = ContentSelector(registry, client=client)

    # Tier 1: 分类 + 打分
    err_console.print(f"[bold]Tier 1: Classifying {len(items)} items...[/bold]")
    items = await classifier.classify_batch(items)

    # Tier 2: 选取 + 去重
    err_console.print(f"[bold]Tier 2: Selecting from {len(items)} items...[/bold]")
    selected = await selector.select(items, use_llm_dedup=True)
    err_console.print(f"[bold]Tier 2 selected {len(selected)} items.[/bold]")

    if not selected:
        err_console.print("[yellow]No items selected after Tier 2.[/yellow]")
        return 0

    # Tier 3: 深度分析
    err_console.print(f"[bold]Tier 3: Analyzing {len(selected)} items with agent loop...[/bold]")
    crag = CRAGEvaluator()
    tool_registry = ToolRegistry()
    loop = AgentLoop(
        client=client,
        registry=tool_registry,
        crag=crag,
        search_chain=SearchChain.build_default(exa_api_key=os.environ.get("EXA_API_KEY")),
        fetch_chain=FetchChain.build_default(firecrawl_api_key=os.environ.get("FIRECRAWL_API_KEY")),
        max_steps=10,
    )

    for i, item in enumerate(selected):
        cat = registry.get_by_path(item.category or "")
        display_name = cat.display_name.get("zh", cat.name) if cat else (item.category or "未知")
        err_console.print(f"[dim]({i + 1}/{len(selected)}) {item.title[:50]}[/dim]")
        try:
            result = await loop.run(item, category_display_name=display_name)
            if item.processing:
                item.processing.deep_analysis = result
        except Exception as e:
            logger.warning("Agent loop failed for %s: %s", item.id, e)

    # 渲染双语简报
    err_console.print("[bold]Rendering bilingual briefings...[/bold]")
    bilingual = render_bilingual(selected, date=datetime.now(timezone.utc))

    # 落盘
    summaries_dir = (project_dir or Path.cwd()) / "data" / "summaries"
    store = SummaryStore(summaries_dir)
    store.save_bilingual(zh=bilingual.zh, en=bilingual.en, date=datetime.now(timezone.utc))
    err_console.print(f"[green]Saved summaries to {summaries_dir}[/green]")

    # 发布
    if not no_publish:
        await _publish(cfg, project_dir, bilingual)
    else:
        err_console.print("[yellow]Skipping publish (--no-publish).[/yellow]")

    console.print(f"\n[bold green]Pipeline complete.[/bold green]")
    console.print(f"  Fetched: {len(items)} items")
    console.print(f"  Selected: {len(selected)} items")
    console.print(f"  Published: {'skipped' if no_publish else 'pages + webhook'}")
    return 0


async def _publish(cfg: Config, project_dir: Path | None, bilingual) -> None:
    """发布简报:GitHub Pages + Webhook。"""
    outputs = cfg.outputs

    # GitHub Pages
    if outputs.get("github_pages", False):
        posts_dir = (project_dir or Path.cwd()) / "docs" / "_posts"
        publisher = GitHubPagesPublisher(posts_dir)
        publisher.publish(zh=bilingual.zh, en=bilingual.en, date=datetime.now(timezone.utc))
        err_console.print(f"[green]Published to GitHub Pages: {posts_dir}[/green]")

    # Webhook
    webhook_configs = outputs.get("webhook", [])
    if webhook_configs:
        webhook_publisher = WebhookPublisher(webhook_configs)
        results = await webhook_publisher.publish(
            content=bilingual.zh[:2000],  # 截断避免过长
            date=datetime.now(timezone.utc),
        )
        success_count = sum(1 for s, _ in results if s)
        err_console.print(f"[green]Webhook: {success_count}/{len(results)} succeeded[/green]")


def main(argv: list[str] | None = None) -> int:
    """CLI 入口:解析参数,分发到对应子命令。"""
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # 加载 .env(若存在),复用 Claude Code 凭证或用户自有 key
    load_dotenv(override=False)

    # TODO: --data-dir 参数应改名为 --project-dir 以匹配实际语义(当前取 parent 作为 project_dir)
    # TODO: --config 参数已定义但未实现(args.config 从未读取),应接入 load_config 或从 build_parser 移除
    project_dir = Path(args.data_dir).parent if args.data_dir else None

    if args.check_config:
        return run_check_config(project_dir)

    if args.fetch_only:
        return asyncio.run(run_fetch_only(project_dir, args.hours))

    if args.classify_only:
        return asyncio.run(run_classify_only(project_dir, args.hours, args.limit))

    if args.select_only:
        return asyncio.run(run_select_only(project_dir, args.hours, args.limit))

    if args.analyze_one:
        return asyncio.run(run_analyze_one(project_dir, args.hours, args.analyze_one))

    # 默认:完整三段式 pipeline
    return asyncio.run(run_pipeline(project_dir, args.hours, args.no_publish, args.limit))


if __name__ == "__main__":
    sys.exit(main())
