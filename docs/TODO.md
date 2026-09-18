# TODO

代码 ↔ TODO.md 双向校验:每条 TODO 对应代码中的 `# TODO` 注释,代码中无遗漏 TODO。

本批重构:砍掉 Tier3 深度 agent 分析,管线简化为两段式(抓取 → Tier1 分类+打分+摘要 → Tier2 选取+去重 → 渲染日报);批量主题去重(大组分块并发);每源截断 30 条控量;新增 video 分类与 168 源(参考 rss-feed)。

---

## 配置加载

| 编号 | 位置 | 问题 | 严重度 |
|---|---|---|---|
| F5 | `src/processing/categories.py:5` | `load_from_raw` 与 `config.py _load_category_configs` 逻辑重复,同一份配置解析两次 | Optional |

## 数据源配置

| 编号 | 位置 | 问题 | 严重度 |
|---|---|---|---|
| E1 | `feeds/research.yml` | Papers with Code 暂无官方 RSS,`papers-other` 子类由期刊会议源填充 | Optional |
| E2 | `feeds/*.yml` | 部分 RSSHub 路由源(B 站/Solidot/V2EX 等)需配 `RSSHUB_BASE_URL`,未配时静默跳过 | Optional |

---

## 汇总

| 严重度 | 数量 |
|---|---|
| Optional | 3(F5/E1/E2) |
| **总计** | **3** |

## 修复优先级

1. **可选清理(Optional)**:F5(去重配置解析)、E1/E2(数据源补全/RSSHub 配置)
