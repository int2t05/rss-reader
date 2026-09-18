# PRD

## 定位

个人信息聚合 + AI 总结系统。抓取 RSS 源(含自建源 auto-trend、视频源),经两段式 pipeline 产出中文每日简报,发布到 GitHub Pages 与 Webhook。

面向单人使用,批处理 cron 形态,无常驻服务。

## 用户故事

- 每日早起 10 分钟掌握 AI/CS/论文/工程/视频领域动态
- 按分类查看简报,同事件多源合并,论文门槛高于新闻
- 自建源(auto-trend)产出 RSS 即可接入,零适配
- 未来可轻松加入财经、加密货币等新领域(配置驱动)

## 功能边界

### 已实现

- RSS 聚合:任意 RSS/Atom,`${VAR}` 环境变量展开,可选 RSSHub 路由,每源截断 30 条控量
- 分类体系:7 大类(ai-research/research/systems/dev-community/tech-news/self-built/video)+ 子类,分类感知阈值 + 配额平衡
- Tier 1:单次 LLM 分类 + 打分 + 摘要(合并调用,减半成本),JSON 修复重试,并发 10
- Tier 2:URL 去重 + 分类阈值过滤 + 主题去重(LLM)+ 配额平衡,零 AI(主题去重除外)
- 中文渲染:产出中文 Markdown 每日简报
- 发布:GitHub Pages(Jekyll front matter)+ Webhook(飞书/Slack/Discord/自定义,并发)
- 落盘:`data/summaries/YYYY-MM-DD.md`
- 跨轮去重:DedupStore(SQLite,WAL)接入 pipeline,已处理项跨轮跳过
- 并发抓取:`asyncio.gather` 并发抓取所有源,单源失败不中断
- 网络重试:`tenacity` 对 429/5xx/超时指数退避(3 次)
- 编排独立:`src/orchestrator.py` 承载 pipeline 编排,`main.py` 仅 CLI 分发
- 模块化:财经/加密货币 `enabled: false` 预留,启用零代码改动

### 未实现(见 TODO)

- 全文抽取(`content_extractor` 字段已定义,未消费)
- Email 发布(SMTP/IMAP)
- 钉钉 Webhook

## 分类树

```
ai-research/    AI 研究     threshold 7.0  limit 8
├── ai-vendor        厂商博客
├── ai-researcher    研究者博客
└── ai-papers        HuggingFace Papers + arXiv cs.AI/LG/CL

research/       论文科研    threshold 7.0  limit 5
├── arxiv-cs         arXiv CS 子类(19)
├── arxiv-stat       arXiv stat.ML/ME/TH
├── arxiv-other      arXiv physics/quant-ph/math/q-bio
└── papers-other     ACL/Nature/Science/MIT/Stanford/CACM/PNAS

systems/        系统工程    threshold 5.0  limit 5
├── eng-blog         大厂工程博客
├── framework        框架官方博客
└── cn-tech          中文技术媒体

dev-community/  开发者社区  threshold 5.0  limit 5
├── github-trending  GitHub Trending
├── github-topics    GitHub Topics
├── forums           HN/Lobsters/Dev.to/TLDR/V2EX/掘金/博客园/开源中国/LinuxDo
└── reddit           r/programming/MachineLearning/webdev/rust/golang/python

tech-news/      科技资讯    threshold 4.0  limit 5
├── cn-news          中文科技媒体
└── en-news          英文科技媒体

self-built/     自建源      threshold 4.0  limit 3
└── auto-trend       auto-trend GitHub Trending 分析

video/          视频        threshold 4.0  limit 3
├── bilibili         B 站 UP 主(RSSHub)
├── youtube          YouTube 频道
└── fluxsift         FluxSift 视频分析(自建)

finance/        财经(预留,enabled: false)
crypto/         加密货币(预留,enabled: false)
```

## 验收标准

- `uv run rss-reader --check-config` 输出分类树与源数量
- `uv run rss-reader --fetch-only --hours 24` 抓取返回非空
- `uv run rss-reader --classify-only --hours 24 --limit 10` 输出分类 + 打分 + 摘要
- `uv run rss-reader --select-only --hours 24 --limit 15` 输出精选 30-50 条
- `uv run rss-reader --hours 24` 完整 pipeline,产出 `data/summaries/` 与 `docs/_posts/`
- `uv run pytest` 全量通过(无 mock,真实数据)
- 日 LLM 调用 < 1000 次

## 术语

| 术语 | 定义 |
|---|---|
| ContentItem | 一条 RSS 条目 |
| category_path | 分类路径,如 `ai-research/ai-papers` |
| Tier 1 | 分类 + 打分 + 摘要(单次 LLM,全量,并发 10) |
| Tier 2 | 选取 + 去重(程序逻辑,零 AI,主题去重除外) |
| DedupStore | 跨轮去重(SQLite,已处理项跳过) |
