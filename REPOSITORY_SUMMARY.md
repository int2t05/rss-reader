# 仓库概览

## 定位

rss-reader 是个人信息聚合 + AI 总结系统,面向单人使用的批处理 CLI。抓取 RSS 源(含自建源 FluxSift、auto-trend),经三段式 pipeline 产出中英双语每日简报,发布到 GitHub Pages 与 Webhook。

## 架构

三段式 pipeline:

```
feeds/*.yml (84 源)
    ↓
Source 层(RSSSource + build_source 工厂)
    ↓ list[ContentItem] 200-500 条
Tier 1: ContentClassifier — 单次 LLM 分类+打分
    ↓
Tier 2: ContentSelector — URL 去重 + 阈值 + 主题去重 + 配额
    ↓ 30-50 条精选
Tier 3: AgentLoop — 有界 ReAct max 10 步 + CRAG + SearchChain/FetchChain
    ↓ AnalysisResult
双语渲染 → 落盘 + GitHub Pages + Webhook
```

## 关键组件

| 组件 | 路径 | 职责 |
|---|---|---|
| Source 层 | `src/sources/` | RSS 抓取,RSSHub 路由,Source Protocol |
| Tier 1 | `src/ai/classifier.py` | 单次 LLM 分类+打分,并发控制,JSON 修复重试 |
| Tier 2 | `src/ai/selector.py` | URL 去重,分类感知阈值,主题去重,配额平衡 |
| Tier 3 | `src/ai/agent/loop.py` | 有界 ReAct 循环,CRAG 评估,工具调用 |
| 降级链 | `src/ai/agent/search_chain.py`、`fetch_chain.py` | Exa→DDG,Firecrawl→trafilatura→httpx |
| SSRF 防护 | `src/ai/agent/ssrf.py` | validate_url 拒绝内网/云元数据 |
| 渲染 | `src/render/` | Markdown 双语渲染 |
| 发布 | `src/publish/` | GitHub Pages(Jekyll)+ Webhook(飞书/Slack/Discord/自定义) |
| 存储 | `src/storage/` | SQLite 去重 + Markdown 总结落盘 |
| 配置 | `src/config.py` | JSON + YAML 加载,${VAR} 展开 |

## 技术栈

Python 3.12+ · uv · httpx · feedparser · pydantic v2 · openai SDK · ddgs · trafilatura · rich · PyYAML · python-dotenv · sqlite3

可选:exa-py(语义搜索)· firecrawl-py(JS 渲染抓取)

## 数据流

1. `load_config` 加载 `data/config.json` + `feeds/*.yml` + `categories/*/category.json`
2. `_fetch_all_items` 顺序抓取所有 enabled 源,返回 `list[ContentItem]`
3. `ContentClassifier.classify_batch` 并发单次 LLM 调用,原地填充 `item.processing.analysis`
4. `ContentSelector.select` 四步选取,返回 30-50 条精选
5. `AgentLoop.run` 对每条精选跑有界 ReAct 循环,填充 `item.processing.deep_analysis`
6. `render_bilingual` 渲染中英两份 Markdown
7. `SummaryStore.save_bilingual` 落盘 + `GitHubPagesPublisher` + `WebhookPublisher` 发布

## 配置

- `data/config.json`:主配置(AI provider、分类、输出)
- `feeds/*.yml`:RSS 源配置(6 文件,84 源)
- `categories/*/category.json`:分类配置(8 分类,6 enabled + 2 预留)
- `.env`:API key 与自建源 URL

## 测试

`test/` 目录,无 mock,真实数据。网络/LLM 测试无 key 时 skip。

## CI

`.github/workflows/daily.yml` 每日 UTC 00:17 跑完整 pipeline,提交 `docs/_posts/` 与 `data/summaries/` 到仓库,GitHub Pages 自动发布。
