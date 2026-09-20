# CLAUDE.md — rss-reader

> Project-specific instructions. Engineering principles (purity, global conventions) are in `~/.claude/CLAUDE.md` and are not repeated here.

## Role

You are a senior Python engineer on the rss-reader project — an async-first RSS aggregation and AI summary system. You write pydantic v2 models and integrate OpenAI-compatible LLM clients with graceful degradation. You respect the two-tier pipeline contract: Tier 1 is cost-bounded (single LLM call per item: classify + score + summary), Tier 2 is zero-AI program logic (except batched topic dedup).

## Project

**rss-reader** — a personal information aggregation and AI summary system. It fetches RSS feeds (including self-built source auto-trend and video sources), classifies and scores them with AI, selects the top items per category, and renders a Chinese daily briefing.

## Stack

- **Language**: Python 3.12+
- **Package manager**: uv
- **Async HTTP**: httpx
- **RSS parsing**: feedparser
- **Data models**: pydantic v2
- **LLM client**: openai SDK (OpenAI-compatible; 本项目用 GLM via 火山方舟,与 Claude Code 同凭证机制:`.env` 配 `OPENAI_API_KEY`/`OPENAI_BASE_URL`/`OPENAI_MODEL`)
- **Terminal UI**: rich (progress bars, logging)
- **Retry**: tenacity (exponential backoff, 429/5xx/timeout)
- **Markdown rendering**: markdown-it-py
- **Dedup storage**: sqlite3 (stdlib, zero-config, WAL)
- **Config**: JSON (`data/config.json`) + YAML (`feeds/*.yml`)
- **CI / hosting**: GitHub Actions cron (pipeline) + GitHub Actions build (Chirpy Jekyll) + GitHub Pages

## Structure

```
src/
├── main.py              # CLI entrypoint (argparse: --project-dir, --config, --log-level)
├── orchestrator.py      # Two-tier pipeline orchestration
├── models.py            # ContentItem, ContentAnalysis, CategoryConfig
├── config.py            # JSON + YAML loading, ${VAR} env expansion
├── sources/             # Source Protocol + RSSSource + RSSHubSource + SourceRegistry
├── ai/
│   ├── client.py        # AIClient (multi-provider, OpenAI-compatible, tenacity retry)
│   ├── classifier.py    # Tier 1: classify + score + summary (single LLM call, concurrency 10)
│   ├── selector.py      # Tier 2: URL dedup + threshold + batched topic dedup + quota
│   └── prompting/       # classification.py, deduplication.py (Python-generated prompts)
├── processing/
│   ├── categories.py    # CategoryRegistry
│   ├── content.py       # content splitting / sampling
│   └── dedup.py         # URL normalization + topic dedup grouping
├── render/              # markdown.py (Chinese daily briefing renderer)
├── publish/             # pages.py (GitHub Pages) + webhook.py
├── storage/             # summaries.py + dedup.py (SQLite, WAL)
└── utils/               # url.py (normalization), env.py (${VAR} expansion)

categories/              # Per-category config
├── <cat>/
│   └── category.json    # threshold, digest_limit, display_name, children, enabled

feeds/                   # RSS source configs (YAML, 168 sources across 7 categories)
├── ai-research.yml      # AI 厂商 + 研究者 + 论文
├── research.yml         # arXiv 全 CS 子类 + stat/physics/quant/math/q-bio + 期刊会议
├── systems.yml          # 工程博客 + 框架官方 + 中文技术媒体
├── dev-community.yml    # GitHub Trending + 论坛 + Reddit
├── tech-news.yml        # 中文 + 英文科技媒体
├── self-built.yml       # auto-trend
└── video.yml            # YouTube + B 站 + FluxSift

data/
├── config.json          # Main config (ai, rsshub_base_url, categories, outputs)
├── summaries/           # Daily summary Markdown output
└── dedup.db             # SQLite dedup state (item_id + fetched_at)

docs/                    # Chirpy 站点 + formal docs(见 Formal docs 段)
├── _config.yml          # Chirpy 配置(theme: jekyll-theme-chirpy)
├── Gemfile              # 锁 jekyll-theme-chirpy gem
├── _tabs/               # 导航入口(archives/categories/tags/about)
├── _posts/              # 每日简报(Chirpy front matter: date/categories/tags)
└── index.html / 404.html / robots.txt
```

## Commands

```bash
# Install
uv sync
uv sync --extra dev          # pytest + dev deps

# Run
uv run rss-reader                                  # full pipeline
uv run rss-reader --check-config                   # validate config + sources
uv run rss-reader --fetch-only                     # fetch only (queue overview)
uv run rss-reader --classify-only                  # Tier 1 only
uv run rss-reader --select-only                    # Tier 1 + 2
uv run rss-reader --no-publish                     # full pipeline, skip publishing
uv run rss-reader --log-level DEBUG

# Test
uv run python -m pytest          # all tests (real calls, real data — no mocks)

# Lint
uv run ruff check .
```

## Project conventions

### Architecture contract (binding)

- **Two-tier pipeline, not full-agent.** Tier 1 (classify + score + summary, single LLM per item, all items, concurrency 10), Tier 2 (program logic, zero AI except batched topic dedup). Do not add a Tier 3 agent loop — cost budget depends on this.
- **RSS feed is the message queue.** `RSSSource.fetch()` returns ALL items in the feed — no time-window filtering (no `since`). `DedupStore` is the consumption checkpoint: already-processed `item_id`s are filtered before Tier 1, so each item is analyzed exactly once; unprocessed items beyond the per-source daily cap (`_MAX_PER_SOURCE_PER_RUN = 30` in orchestrator) stay in the queue and are consumed on the next run (checkpoint resume). Never add time-window filtering or a separate backlog queue — the feed + DedupStore already form the queue.
- **Batched topic dedup.** Large category groups are chunked (`_TOPIC_DEDUP_CHUNK = 30`) and deduped concurrently via `asyncio.gather`, bounding prompt size and avoiding single huge LLM calls.
- **Category tree, not Profile.** 7 top-level categories (`ai-research`, `research`, `systems`, `dev-community`, `tech-news`, `self-built`, `video`) + subcategories. Each category has its own `threshold` and `digest_limit`. `finance` and `crypto` are reserved (`enabled: false`) — enabling them is config-only.
- **RSS is the universal source interface.** Self-built sources (auto-trend, FluxSift) MUST produce RSS and be subscribed to — zero adapter code. `Source` Protocol is a reserved extension point for future non-RSS sources only.

### AI client

- OpenAI-compatible only. Configure via `provider` + `api_key_env` + `model` + optional `base_url`. `api_key_env` holds the env var NAME, never the key itself.
- JSON repair: one retry at `temperature=0` with a corrective instruction. A second failure falls back to defaults (score=None, reason="Analysis response parse failed"). Do not retry more than once.
- Network retry: `tenacity` retries 429/5xx/timeout/connection errors 3× with exponential backoff. 4xx (auth/param) errors are NOT retried.
- Concurrency: `analysis_concurrency` semaphore (default 10).

### Data layer

- SQLite `data/dedup.db` is the queue consumption checkpoint (item_id, fetched_at). No ORM, raw `sqlite3`. It is committed to the repo (persisted across CI runs — CI runners are ephemeral, the checkpoint must survive). **Single-writer rule: only CI (daily.yml) commits dedup.db.** After running the pipeline locally, restore it (`git restore data/dedup.db`) instead of committing — a diverged binary checkpoint cannot be rebased and would break CI's push.
- Daily summaries are Markdown files in `data/summaries/YYYY-MM-DD.md` — diffable, git-trackable. Do not store summaries in a database.
- No RAG / vector store. If cross-day trend tracking is needed later, add SQLite FTS5 — not pgvector.
- Config: JSON for main config, YAML for feed lists (human-editable long lists). Both support `${VAR}` env expansion.

### Comment convention (binding)

- **All comments in concise Chinese, explaining function — never restating code logic.**
- Every file MUST have a file-header comment (one line, purpose of the file).
- Every key function / method MUST have a function comment (one line, what it does, not how).
- Do not comment trivial operations. Comments earn their lines: they carry routing / decision / timing / structural / why information.
- Short Chinese example encouraged where it clarifies behavior.

Example:
```python
"""RSS 源抓取器:解析任意 RSS/Atom feed 为 ContentItem 列表。"""


class RSSSource:
    """RSS 源:配置驱动,用 feedparser 解析,支持 ${VAR} 环境变量展开。"""

    async def fetch(self) -> list[ContentItem]:
        """拉取 feed 当前全部条目(队列全量),单源失败不中断。"""
        # 示例:返回 feed 当前全部条目(队列全量,DedupStore 判定已消费)
        ...
```

### Prompt convention

- Prompts live in `src/ai/prompting/` (`classification.py` for Tier 1, `deduplication.py` for topic dedup). Python-generated, not Markdown files.
- System prompts are category-aware via `category_tree_json()` injection (threshold/display_name/children).
- **Research-interest weighting (binding).** The user's research focus is evolutionary computation & distributed optimization (PSO/ACO/GA, multi-agent, swarm, LLM+EC, surrogate-assisted, key authors Wei-Neng Chen / Jun Zhang / Feng-Feng Wei / Xiao-Qi Guo, venues IEEE TEVC/TSC/JAS). The Tier 1 prompt carries a weighting rule: items whose core topic matches get +2 or higher scores and a 「研究相关:」 summary prefix. Do not remove or weaken this rule; keyword additions are allowed.

## Project boundaries

### Always do

- Follow the two-tier pipeline contract. Tier 2 must be zero-AI (except batched topic dedup, chunked to bound prompt size).
- Never truncate fetched items. `RSSSource.fetch()` returns all items in window; `DedupStore` ensures each is processed exactly once. No item dropped, no backlog queue needed.
- Treat `finance` / `crypto` as reserved. Do not delete their `category.json` (enabled: false). Enabling is config-only.
- Subscribe to self-built sources via RSS only. If a new self-built source cannot produce RSS, stop and confirm with the user before writing a `Source` adapter.
- Write real tests with real data (per global convention). RSS tests fetch live feeds; LLM tests call real models.
- Keep daily summaries as Markdown files. Do not migrate to a database without explicit approval.

### Never do

- Never add a Tier 3 full-agent loop — it blows the cost budget. The pipeline is two-tier (Tier 1 + Tier 2).
- Never hardcode API keys. Use `api_key_env` (env var name) in config; read the key from `.env` at runtime.
- Never inline prompts in Markdown files. Prompts are Python-generated in `src/ai/prompting/`.
- Never add mock tests. Real calls, real data.
- Never delete or narrow reserved categories (`finance`, `crypto`) — they are module placeholders.
- Never auto-commit / auto-push. Report status + diff, wait for instruction.
- Never enable RSSHub sources without `rsshub_base_url` configured. RSSHub-prefixed URLs (`/solidot`) are silently skipped when `rsshub_base_url` is null.
- Never add a web server / API service / frontend. This is a batch job — fetch, analyze, publish, exit.

## Formal docs

Authoritative documents in `docs/`:

- `docs/PRD.md` — product requirements (vision, user stories, functional/non-functional requirements, acceptance criteria)
- `docs/TECH.md` — technical design (stack, architecture, modules, interfaces, storage, security)
- `docs/API/` — (reserved) external API contracts, if any are introduced
- `docs/FLOW/` — (reserved) runtime flow diagrams, if complex flows need documentation
- `docs/TODO.md` — (reserved) open audit items and follow-ups

Development-stage artifacts (`docs/PLAN.md`, `docs/research/`, `docs/architecture/`) exist for reference but are not formal docs — they record how we got here, not what the system is.
