# rss-reader

> 个人信息聚合 + AI 总结系统 — RSS × 三段式 pipeline × 有界 ReAct agent

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![uv](https://img.shields.io/badge/uv-4B275F?style=flat-square&logo=uv&logoColor=white)](https://github.com/astral-sh/uv)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen?style=flat-square)](test/)
[![LLM](https://img.shields.io/badge/LLM-OpenAI%20compatible-f0daba?style=flat-square&logo=openai&logoColor=black)](docs/TECH.md)
[![RSS](https://img.shields.io/badge/sources-84%20feeds-f97316?style=flat-square&logo=rss&logoColor=white)](feeds/)

抓取 RSS 源(含自建源 FluxSift、auto-trend),经三段式 pipeline 产出中英双语每日简报,发布到 GitHub Pages 与 Webhook。

**特色**:三段式 pipeline(高量低精 → 零 AI → 低量高精)在成本与深度间取得平衡,日 LLM 调用 < 1000 次;有界 ReAct agent 循环带 CRAG 评估与降级链联网补充;6 大类分类树 + 分类感知阈值保证多样性与重点突出;自建源产出 RSS 即可接入,零适配。

## 快速开始

```bash
uv sync --extra dev
cp .env.example .env  # 填入 OPENAI_API_KEY(必填)
uv run rss-reader --check-config
uv run rss-reader --hours 24
```

## 使用

```bash
# 完整 pipeline(默认)
uv run rss-reader --hours 24

# 分阶段
uv run rss-reader --fetch-only --hours 24
uv run rss-reader --classify-only --hours 24 --limit 10
uv run rss-reader --select-only --hours 24 --limit 15
uv run rss-reader --analyze-one <item_id> --hours 24
uv run rss-reader --hours 24 --no-publish

# 测试(无 mock,真实数据)
uv run pytest
```

## 架构

```mermaid
flowchart LR
    FEEDS[feeds/*.yml<br/>84 源] --> SRC[Source 层<br/>RSSSource]
    SRC --> T1[Tier 1<br/>分类+打分 单次 LLM]
    T1 --> T2[Tier 2<br/>选取+去重 零 AI]
    T2 --> T3[Tier 3<br/>Agent 循环 max 10 步]
    T3 --> RND[双语渲染]
    RND --> OUT[GitHub Pages<br/>Webhook<br/>data/summaries/]
```

**三段式 pipeline**:
- **Tier 1**(高量低精):全量条目单次 LLM 分类 + 打分
- **Tier 2**(零 AI):URL 去重 + 分类感知阈值 + 主题去重 + 配额平衡
- **Tier 3**(低量高精):有界 ReAct 循环,CRAG 评估联网,SearchChain + FetchChain 降级链

## 功能

- 6 大类 + 子类分类树,分类感知阈值与配额
- CRAG 联网评估(strong 跳过 / weak 强制 / ambiguous 自主)
- SearchChain(Exa → DuckDuckGo)+ FetchChain(Firecrawl → trafilatura → httpx)降级链
- SSRF 防护
- 双语简报(中/英)
- GitHub Pages(Jekyll)+ Webhook(飞书/Slack/Discord/自定义)
- 自建源 RSS 接入零适配
- 财经/加密货币分类预留,启用零代码

## 项目方向

- **SSRF 加固**:IPv6 阻断、DNS Rebinding 防护、重定向目标校验
- **Agent 循环增强**:多消息对话支持、并行工具调用、per-tool-type 限制
- **并发抓取**:`asyncio.gather` 替代顺序抓取
- **orchestrator 抽取**:pipeline 编排独立模块
- **全文抽取 / Email 发布 / 断点续跑 / 钉钉 Webhook**

完整 TODO 见 `docs/TODO.md`。

## 文档

| 文档 | 说明 |
|---|---|
| `docs/PRD.md` | 产品需求 |
| `docs/TECH.md` | 技术方案 |
| `docs/API/README.md` | CLI 接口 + 配置 schema + 数据模型 |
| `docs/FLOW/README.md` | 业务流程 + 数据流 |
| `docs/TODO.md` | 不足与未来方向 |

## 贡献

欢迎 issue 与 PR。请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

## License

[MIT](LICENSE)
