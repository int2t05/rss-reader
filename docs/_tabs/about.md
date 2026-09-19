---
layout: page
title: 关于
icon: fas fa-info-circle
order: 4
---

# rss-reader

个人信息聚合 + AI 总结系统。抓取 RSS 源(含自建源 auto-trend、视频源),经两段式 pipeline 产出中文每日简报。

- **Tier 1**:分类 + 打分 + 摘要(单次 LLM,并发 10)
- **Tier 2**:URL 去重 + 分类阈值 + 批量主题去重 + 配额平衡
- **DedupStore**:跨轮去重,每条目恰好处理一次

源码:[github.com/int2t05/rss-reader](https://github.com/int2t05/rss-reader)
