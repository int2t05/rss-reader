# 仓库概览

## 定位

rss-reader 是个人信息聚合 + AI 总结系统,面向单人使用的批处理 CLI。抓取 RSS 源(含自建源 FluxSift、auto-trend),经三段式 pipeline 产出中英双语每日简报,发布到 GitHub Pages 与 Webhook。

## 架构

三段式 pipeline:

```
feeds/*.yml (168 源)
    ↓
Source 层(RSSSource + build_source 工厂,并发抓取,每源截断 30 条)
    ↓ list[ContentItem] ~500-1000 条
Tier 1: ContentClassifier — 单次 LLM 分类+打分+摘要(并发 10)
    ↓
Tier 2: ContentSelector — URL 去重 + 阈值 + 批量主题去重(分块并发)+ 配额
    ↓ 30-50 条精选
中文日报渲染 → 落盘 + GitHub Pages + Webhook
```

## 关键组件

| 组件 | 路径 | 职责 |
|---|---|---|
| Source 层 | `src/sources/` | RSS 抓取,RSSHub 路由,每源截断 30 条,Source Protocol |
| Tier 1 | `src/ai/classifier.py` | 单次 LLM 分类+打分+摘要,并发 10,JSON 修复重试 |
| Tier 2 | `src/ai/selector.py` | URL 去重,分类感知阈值,批量主题去重(分块并发),配额平衡 |
| 渲染 | `src/render/` | Markdown 中文日报渲染 |
| 发布 | `src/publish/` | GitHub Pages(Jekyll)+ Webhook(飞书/Slack/Discord/自定义,并发) |
| 存储 | `src/storage/` | SQLite 去重(WAL)+ Markdown 总结落盘 |
| 配置 | `src/config.py` | JSON + YAML 加载,${VAR} 展开 |

## 技术栈

Python 3.12+ · uv · httpx · feedparser · pydantic v2 · openai SDK · tenacity · rich · PyYAML · python-dotenv · sqlite3

## 数据流

1. `load_config` 加载 `data/config.json` + `feeds/*.yml` + `categories/*/category.json`
2. `_fetch_all_items` 用 `asyncio.gather` 并发抓取所有 enabled 源,每源截断 30 条,DedupStore 过滤已处理项,返回 `list[ContentItem]`
3. `ContentClassifier.classify_batch` 并发 10 单次 LLM 调用,原地填充 `item.processing.analysis`(分类+分数+摘要)
4. `ContentSelector.select` 四步选取,返回 30-50 条精选
5. `render_markdown` 渲染中文 Markdown 日报
6. `SummaryStore.save` 落盘 + `GitHubPagesPublisher` + `WebhookPublisher` 发布 + DedupStore 标记已处理

## 配置

- `data/config.json`:主配置(AI provider、分类、输出)
- `feeds/*.yml`:RSS 源配置(7 文件,168 源)
- `categories/*/category.json`:分类配置(9 分类,7 enabled + 2 预留)
- `.env`:API key 与自建源 URL

## 测试

`test/` 目录,无 mock,真实数据。网络/LLM 测试无 key 时 skip。

## CI

`.github/workflows/daily.yml` 每日 UTC 00:17 跑完整 pipeline,提交 `docs/_posts/` 与 `data/summaries/` 到仓库,GitHub Pages 自动发布。
