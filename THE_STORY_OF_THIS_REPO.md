# 仓库故事

## 起点

rss-reader 源于一个简单需求:每天花 10 分钟掌握 AI/CS/论文/工程领域动态,而不是在 RSS 阅读器里漫无目的翻阅。

市面上的工具要么只聚合不分析(RSS 阅读器),要么不支持 RSS(AI 简报工具),要么分类太粗、重点不突出、无联网补充。

## 设计决策

### 为什么是三段式 pipeline,而非全 agent

全 agent 模式每条 RSS 条目都跑 agent 循环,200-500 条/天 × 5 步/条 = 1000-2500 次 LLM 调用/天。成本过高。

三段式 pipeline:Tier1 高量低精(单次 LLM,全量)→ Tier2 零 AI(程序逻辑)→ Tier3 低量高精(agent 循环,精选 30-50 条)。日调用 350-750 次,降 60-70%。

### 为什么是分类树,而非固定 Profile

参考项目 Horizon 有 4 套固定 Profile,同类源混排,无法差异化。rss-reader 用 6 大类 + 子类,分类感知阈值(论文 7 分才算重点,新闻 4 分即可)+ 配额平衡,保证多样性与重点突出。

### 为什么是 CRAG 评估,而非强联网

强联网不经济,每条都联网成本高。CRAG 评估内容充分性:strong(>2000 字符 + 技术细节)跳过联网,weak(<500 字符)强制联网,ambiguous 自主决策。

### 为什么是降级链,而非单后端

搜索与抓取后端可能不可用(网络限制、API key 缺失)。SearchChain(Exa → DuckDuckGo)与 FetchChain(Firecrawl → trafilatura → httpx)按优先级尝试,首个成功返回,末位零配置兜底,永不断路。

### 为什么自建源走 RSS

FluxSift(B站/抖音收藏夹分析)与 auto-trend(GitHub Trending 分析)都产出 RSS,新系统直接订阅,零适配代码。未来自建源产出 RSS 即可接入。Source Protocol 作为扩展点,给未来非 RSS 源留接口。

### 为什么借鉴 Cognik 但从零写

Cognik(Go)有完整的 ReAct 循环 + CRAG + 降级链抽象,但过重(工单、RBAC、Next.js 前端、PostgreSQL+pgvector)。rss-reader 借鉴 Cognik 的 agent 抽象设计,翻译为 Python,不复制代码,不带历史包袱。

## 参考项目

| 项目 | 借鉴点 |
|---|---|
| Horizon | RSS 抓取、多 provider AI、多输出渠道、Profile→Category |
| Cognik | Tool/Registry、ReAct Loop、SearchChain/FetchChain、CRAG、SSRF |
| rss-feed | 114 个 RSS 源分类(舍弃 video,保留约 90 个) |
| FluxSift | 自建源 RSS 模式,Collector Protocol 设计参考 |
| auto-trend | feeds.yml schema,LLM 结构化 JSON 分析模式 |

## 当前阶段

rss-reader 核心实现完成:三段式 pipeline 端到端跑通,84 源配置就绪,6 大类分类树,双语简报产出,GitHub Pages 与 Webhook 发布,CI 每日自动跑。

待改进的方向(见 `docs/TODO.md`):
- SSRF 加固(IPv6、DNS Rebinding、重定向)
- Agent 循环增强(多消息对话、并行工具调用、per-tool-type 限制)
- 并发抓取与 orchestrator 抽取
- 全文抽取、Email 发布、断点续跑、钉钉 Webhook

## 技术选型理由

- **Python**:与 FluxSift/auto-trend/Horizon 生态一致,子项目天然兼容
- **uv**:与 Horizon/FluxSift 一致的包管理
- **httpx trust_env=False**:避免 Windows 系统代理干扰抓取(实战踩坑)
- **SQLite**:零配置,去重状态存储
- **Jekyll**:GitHub Pages 原生,无需额外构建
- **无 mock 测试**:真实数据验证,网络不可达时 skip 而非伪造
