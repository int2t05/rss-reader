"""两段式 pipeline 编排:消费 RSS 队列 → Tier1 分类+打分+摘要 → Tier2 选取+去重 → 渲染日报 → 落盘+发布。

RSS feed 即消息队列,DedupStore 即消费位点(断点续传),每源每日消费上限控制成本。
从 CLI 入口(main.py)抽出纯编排逻辑,便于测试与复用。各 run_* 子命令对应 CLI 子命令。
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
from rich.console import Console
from rich.table import Table

from src.ai.classifier import ContentClassifier
from src.ai.client import AIClient, AIClientConfig
from src.ai.selector import ContentSelector
from src.config import Config, load_config
from src.processing.categories import CategoryRegistry
from src.publish.pages import GitHubPagesPublisher
from src.publish.webhook import WebhookPublisher
from src.render.markdown import render_markdown
from src.sources.registry import SourceRegistry
from src.sources.rsshub import build_source
from src.storage.dedup import DedupStore
from src.storage.summaries import SummaryStore

logger = logging.getLogger(__name__)
console = Console()  # 结果输出走 stdout,便于管道
err_console = Console(stderr=True)  # 进度/告警走 stderr

# 每源每日处理上限:RSS feed 是消息队列,DedupStore 是消费位点;
# 超出上限的未处理条目留在队列里,下次运行继续消费(断点续传)。
_MAX_PER_SOURCE_PER_RUN = 30


def _build_registry(cfg: Config, http_client: httpx.AsyncClient) -> SourceRegistry:
    """从配置构建 SourceRegistry:RSSHub 路由源根据 rsshub_base_url 决定跳过或解析。"""
    registry = SourceRegistry()
    for src_cfg in cfg.sources:
        source = build_source(src_cfg, cfg.rsshub_base_url, http_client)
        if source is not None:
            registry.register(source)
    return registry


async def _fetch_all_items(cfg: Config, dedup_store: DedupStore | None = None) -> list:
    """消费 RSS 消息队列:每源取未处理条目的前 _MAX_PER_SOURCE_PER_RUN 条。

    RSS feed 即队列(自带条目保留),DedupStore 即消费位点(已处理记录)。
    每源每日上限控制 Tier1 成本;超限条目不标记,下次运行从位点继续。
    单源失败不中断。
    """
    async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
        registry = _build_registry(cfg, client)
        per_source = await _gather_fetches(registry)

    items: list = []
    for source_items in per_source:
        if dedup_store is not None and source_items:
            item_ids = [it.id for it in source_items]
            unprocessed = set(dedup_store.batch_unprocessed(item_ids))
            source_items = [it for it in source_items if it.id in unprocessed]
        items.extend(source_items[:_MAX_PER_SOURCE_PER_RUN])
    return items


async def _gather_fetches(registry: SourceRegistry) -> list[list]:
    """并发执行所有源 fetch,返回按源分组的条目列表。单源失败记 warning 返回空组。"""
    sources = registry.all()
    results = await asyncio.gather(
        *(source.fetch() for source in sources),
        return_exceptions=True,
    )
    per_source: list[list] = []
    for source, result in zip(sources, results, strict=True):
        if isinstance(result, Exception):
            logger.warning("Source %s failed: %s", source.category, result)
            per_source.append([])
        else:
            per_source.append(result)
    return per_source


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
    )
    return AIClient(client_cfg)


def _build_category_registry(cfg: Config, project_dir: Path | None) -> CategoryRegistry:
    """从配置构造 CategoryRegistry,加载 enabled 分类。"""
    categories_root = (project_dir or Path.cwd()) / "categories"
    reg = CategoryRegistry(categories_root)
    reg.load_from_raw(cfg.categories)
    return reg


def run_check_config(project_dir: Path | None, config_path: str | None = None) -> int:
    """--check-config:加载配置,输出源数量与分类列表,返回退出码。"""
    try:
        cfg = load_config(project_dir, config_path)
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


async def run_fetch_only(project_dir: Path | None, config_path: str | None = None) -> int:
    """--fetch-only:并发抓取所有源,输出每源条目数与总数,返回退出码。"""
    try:
        cfg = load_config(project_dir, config_path)
    except FileNotFoundError as e:
        err_console.print(f"[red]Config error:[/red] {e}")
        return 1

    total = 0
    async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
        registry = _build_registry(cfg, client)
        if len(registry) == 0:
            err_console.print("[yellow]No enabled sources.[/yellow]")
            return 0

        per_source: list[tuple[str, int]] = []
        for source in registry.all():
            try:
                items = await source.fetch()
                per_source.append((source.config.name if hasattr(source, "config") else source.category, len(items)))
                total += len(items)
            except Exception as e:
                logger.warning("Source %s failed: %s", source.category, e)
                per_source.append((source.category, 0))

    table = Table(title="Fetched from feed queue")
    table.add_column("Source", style="cyan")
    table.add_column("Items", style="green", justify="right")
    for name, count in per_source:
        table.add_row(name, str(count))
    table.add_row("[bold]Total[/bold]", f"[bold]{total}[/bold]")
    console.print(table)
    return 0


async def run_classify_only(
    project_dir: Path | None, limit: int | None, config_path: str | None = None
) -> int:
    """--classify-only:抓取 → Tier1 分类+打分,输出结果表格。"""
    try:
        cfg = load_config(project_dir, config_path)
    except FileNotFoundError as e:
        err_console.print(f"[red]Config error:[/red] {e}")
        return 1

    items = await _fetch_all_items(cfg)
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


async def run_select_only(
    project_dir: Path | None, limit: int | None, config_path: str | None = None
) -> int:
    """--select-only:抓取 → Tier1 分类+打分 → Tier2 选取+去重,输出精选结果表格。"""
    try:
        cfg = load_config(project_dir, config_path)
    except FileNotFoundError as e:
        err_console.print(f"[red]Config error:[/red] {e}")
        return 1

    items = await _fetch_all_items(cfg)
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


async def run_pipeline(
    project_dir: Path | None,
    no_publish: bool,
    limit: int | None,
    config_path: str | None = None,
) -> int:
    """完整 pipeline:消费队列 → Tier1 分类+打分+摘要 → Tier2 选取+去重 → 渲染日报 → 落盘 + 发布。

    每源消费未处理条目的前 _MAX_PER_SOURCE_PER_RUN 条,处理后标记(消费位点),
    超限条目下次运行继续。--no-publish 跳过发布,仅落盘到 data/summaries/。
    """
    try:
        cfg = load_config(project_dir, config_path)
    except FileNotFoundError as e:
        err_console.print(f"[red]Config error:[/red] {e}")
        return 1

    items = await _fetch_all_items(cfg, dedup_store=_dedup_store(project_dir))
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

    # Tier 1: 分类 + 打分 + 摘要
    err_console.print(f"[bold]Tier 1: Classifying {len(items)} items...[/bold]")
    items = await classifier.classify_batch(items)

    # Tier 2: 选取 + 去重
    err_console.print(f"[bold]Tier 2: Selecting from {len(items)} items...[/bold]")
    selected = await selector.select(items, use_llm_dedup=True)
    err_console.print(f"[bold]Tier 2 selected {len(selected)} items.[/bold]")

    if not selected:
        _mark_processed(project_dir, items)
        err_console.print("[yellow]No items selected after Tier 2.[/yellow]")
        return 0

    # 渲染中文日报
    err_console.print("[bold]Rendering daily briefing...[/bold]")
    content = render_markdown(selected, date=datetime.now(timezone.utc))

    # 落盘
    summaries_dir = (project_dir or Path.cwd()) / "data" / "summaries"
    store = SummaryStore(summaries_dir)
    store.save(content=content, date=datetime.now(timezone.utc))
    err_console.print(f"[green]Saved summaries to {summaries_dir}[/green]")

    # 发布
    if not no_publish:
        await _publish(cfg, project_dir, content)
    else:
        err_console.print("[yellow]Skipping publish (--no-publish).[/yellow]")

    # 跨轮去重:标记本轮处理的 item,下次 pipeline 跳过(省 AI 调用)
    _mark_processed(project_dir, items)

    console.print("\n[bold green]Pipeline complete.[/bold green]")
    console.print(f"  Fetched: {len(items)} items")
    console.print(f"  Selected: {len(selected)} items")
    console.print(f"  Published: {'skipped' if no_publish else 'pages + webhook'}")
    return 0


def _dedup_store(project_dir: Path | None) -> DedupStore:
    """构造 DedupStore:project_dir/data/dedup.db。"""
    db_path = (project_dir or Path.cwd()) / "data" / "dedup.db"
    return DedupStore(db_path)


def _mark_processed(project_dir: Path | None, items: list) -> None:
    """批量标记 item 为已处理(跨轮去重)。"""
    if not items:
        return
    store = _dedup_store(project_dir)
    for item in items:
        store.mark_processed(item.id)
    store.close()


async def _publish(cfg: Config, project_dir: Path | None, content: str) -> None:
    """发布简报:GitHub Pages + Webhook。"""
    outputs = cfg.outputs

    # GitHub Pages
    if outputs.get("github_pages", False):
        posts_dir = (project_dir or Path.cwd()) / "docs" / "_posts"
        publisher = GitHubPagesPublisher(posts_dir)
        publisher.publish(content=content, date=datetime.now(timezone.utc))
        err_console.print(f"[green]Published to GitHub Pages: {posts_dir}[/green]")

    # Webhook
    webhook_configs = outputs.get("webhook", [])
    if webhook_configs:
        webhook_publisher = WebhookPublisher(webhook_configs)
        results = await webhook_publisher.publish(
            content=content[:2000],  # 截断避免过长
            date=datetime.now(timezone.utc),
        )
        success_count = sum(1 for s, _ in results if s)
        err_console.print(f"[green]Webhook: {success_count}/{len(results)} succeeded[/green]")
