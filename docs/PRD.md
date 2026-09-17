# PRD

## 定位

个人信息聚合 + AI 总结系统。抓取 RSS 源(含自建源 FluxSift、auto-trend),经三段式 pipeline 产出中英双语每日简报,发布到 GitHub Pages 与 Webhook。

面向单人使用,批处理 cron 形态,无常驻服务。

## 用户故事

- 每日早起 10 分钟掌握 AI/CS/论文/工程领域动态
- 按分类查看简报,同事件多源合并,论文门槛高于新闻
- AI 对精选条目联网补充背景,产出结构化深度分析
- 自建源(FluxSift/auto-trend)产出 RSS 即可接入,零适配
- 未来可轻松加入财经、加密货币等新领域(配置驱动)

## 功能边界

### 已实现

- RSS 聚合:任意 RSS/Atom,`${VAR}` 环境变量展开,可选 RSSHub 路由
- 分类体系:6 大类 + 子类,分类感知阈值 + 配额平衡
- Tier 1:单次 LLM 分类 + 打分(合并调用,减半成本),JSON 修复重试
- Tier 2:URL 去重 + 分类阈值过滤 + 主题去重(LLM)+ 配额平衡,零 AI(主题去重除外)
- Tier 3:有界 ReAct 循环(max 10 步),CRAG 评估联网,SearchChain + FetchChain 降级链
- 联网补充:Exa → DuckDuckGo 搜索降级,Firecrawl → trafilatura → httpx 抓取降级,SSRF 防护
- 双语渲染:同一份源数据产出中英两份 Markdown
- 发布:GitHub Pages(Jekyll front matter)+ Webhook(飞书/Slack/Discord/自定义)
- 落盘:`data/summaries/YYYY-MM-DD-{zh,en}.md`
- 模块化:财经/加密货币 `enabled: false` 预留,启用零代码改动

### 未实现(见 TODO)

- 全文抽取(`content_extractor` 字段已定义,未消费)
- Email 发布(SMTP/IMAP)
- 钉钉 Webhook
- 断点续跑(`DedupStore` 已实现,未接入 pipeline)
- 并发抓取(当前顺序执行)
- orchestrator 独立模块(当前内联 main.py)

## 分类树

```
ai-research/    AI 研究     threshold 7.0  limit 8
├── ai-vendor        厂商博客
├── ai-researcher    研究者博客
└── ai-papers        HuggingFace Papers + arXiv cs.AI/LG/CL

research/       论文科研    threshold 7.0  limit 5
├── arxiv-cs         arXiv CS 子类
├── arxiv-stat       arXiv stat.ML
└── papers-other     Papers with Code(预留)

systems/        系统工程    threshold 5.0  limit 5
├── eng-blog         大厂工程博客
├── framework        框架官方博客
└── cn-tech          中文技术媒体

dev-community/  开发者社区  threshold 5.0  limit 5
├── github-trending  GitHub Trending
├── github-topics    GitHub Topics
├── forums           HN/Lobsters/Dev.to/TLDR
└── reddit           r/programming, r/MachineLearning

tech-news/      科技资讯    threshold 4.0  limit 5
├── cn-news          中文科技媒体
└── en-news          英文科技媒体

self-built/     自建源      threshold 4.0  limit 3
├── fluxsift         FluxSift
└── auto-trend       auto-trend

finance/        财经(预留,enabled: false)
crypto/         加密货币(预留,enabled: false)
```

## 验收标准

- `uv run rss-reader --check-config` 输出分类树与源数量
- `uv run rss-reader --fetch-only --hours 24` 抓取返回非空
- `uv run rss-reader --classify-only --hours 24 --limit 10` 输出分类 + 打分
- `uv run rss-reader --select-only --hours 24 --limit 15` 输出精选 30-50 条
- `uv run rss-reader --analyze-one <id> --hours 24` 输出 Tier 3 深度分析
- `uv run rss-reader --hours 24` 完整 pipeline,产出 `data/summaries/` 与 `docs/_posts/`
- `uv run pytest` 全量通过(无 mock,真实数据)
- 日 LLM 调用 < 1000 次

## 术语

| 术语 | 定义 |
|---|---|
| ContentItem | 一条 RSS 条目 |
| category_path | 分类路径,如 `ai-research/ai-papers` |
| Tier 1 | 分类 + 打分(单次 LLM,全量) |
| Tier 2 | 选取 + 去重(程序逻辑,零 AI) |
| Tier 3 | 深度分析(有界 ReAct,精选) |
| CRAG | 充分性评估(strong/ambiguous/weak) |
| SearchChain | 搜索降级链(Exa → DuckDuckGo) |
| FetchChain | 抓取降级链(Firecrawl → trafilatura → httpx) |
