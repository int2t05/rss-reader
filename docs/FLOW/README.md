# FLOW

## 完整 pipeline

```mermaid
flowchart TB
    START([uv run rss-reader --hours 24]) --> LOAD[load_config<br/>data/config.json + feeds/*.yml + categories/*]
    LOAD --> FETCH[_fetch_all_items<br/>asyncio.gather 并发抓取]
    FETCH --> T1[ContentClassifier.classify_batch<br/>Tier1: 单次 LLM 分类+打分+摘要]
    T1 --> T2[ContentSelector.select<br/>Tier2: 选取+去重]
    T2 --> RND[render_markdown<br/>中文日报]
    RND --> SUM[SummaryStore.save<br/>data/summaries/]
    RND --> PUB[_publish<br/>Pages + Webhook]
    PUB --> DEDUP[_mark_processed<br/>跨轮去重]
    DEDUP --> DONE([Pipeline complete])
```

## Tier 1:分类 + 打分 + 摘要

```mermaid
flowchart LR
    ITEMS[list[ContentItem]<br/>~500-1000 条] --> BATCH[classify_batch<br/>Semaphore 并发 10]
    BATCH --> LOOP{每条 item}
    LOOP --> HINT[源级 category hint]
    HINT --> PROMPT[构建 system + user prompt]
    PROMPT --> LLM1[LLM complete<br/>temperature=0.7]
    LLM1 --> PARSE[parse_json_response]
    PARSE -->|失败| RETRY[修复重试<br/>temperature=0]
    RETRY --> PARSE2[parse_json_response]
    PARSE -->|成功| RESULT[ContentAnalysis<br/>category_path + score + summary + tags]
    PARSE2 -->|失败| DEFAULT[默认 analysis<br/>score=0.0]
    RESULT --> SET[item.processing.analysis = result]
    DEFAULT --> SET
    SET --> NEXT{下一条}
    NEXT -->|完成| OUT[带 analysis 的 items]
```

**数据**:输入 `list[ContentItem]`(无 analysis),输出同列表(items 原地修改,`processing.analysis` 填充)。

**并发**:`analysis_concurrency=10` Semaphore,单条失败写入默认 analysis 不中断。

## Tier 2:选取 + 去重

```mermaid
flowchart TB
    IN[带 analysis 的 items] --> D1[dedup_by_url<br/>URL 规范化 + 保留高分]
    D1 --> D2[_filter_by_threshold<br/>分类感知阈值]
    D2 --> D3[_topic_dedup<br/>按父分类分组 LLM 判断同事件]
    D3 --> D4[_apply_quota<br/>分类配额 + 分数降序]
    D4 --> OUT[30-50 精选 items]
```

**四步**:
1. `normalize_url` 去 fragment/追踪参数/统一 https/小写 host,同 URL 保留分数最高
2. 每分类独立 threshold(ai-research 7.0 / tech-news 4.0),低于阈值丢弃
3. 按父分类前缀分组(如 `ai-research/ai-vendor` 与 `ai-research/ai-papers` 归 `ai-research`),每组 LLM 判断同事件,保留高分
4. 每分类 `digest_limit` 截取,按分数降序

**数据**:输入 `list[ContentItem]`(带 analysis),输出 30-50 条精选(带 analysis)。

## 中文渲染 + 发布

```mermaid
flowchart LR
    ITEMS[带 analysis 的 items] --> MD[render_markdown<br/>中文日报]
    MD --> SUM[SummaryStore.save<br/>data/summaries/YYYY-MM-DD.md]
    MD --> PAGES[GitHubPagesPublisher<br/>docs/_posts/YYYY-MM-DD.md<br/>Jekyll front matter]
    MD --> HOOK{webhook 配置?}
    HOOK -->|是| WH[WebhookPublisher<br/>asyncio.gather 并发<br/>Feishu/Slack/Discord/Custom]
    HOOK -->|否| SKIP[跳过]
```

## 分类配置加载

```mermaid
flowchart LR
    JSON[data/config.json<br/>categories 段] --> REG[CategoryRegistry.load_from_raw]
    DIR[categories/ 目录] --> FILE{category.json 存在?}
    FILE -->|是| MERGE[merged = raw + category.json]
    FILE -->|否| RAW[merged = raw]
    MERGE --> REG
    RAW --> REG
    REG --> ENABLED[过滤 enabled=True]
    ENABLED --> LIST[list[CategoryConfig]]
```

## Source 抓取

```mermaid
flowchart TB
    CFG[RSSSourceConfig] --> BUILD[build_source]
    BUILD --> ISRSSHUB{url 以 / 开头?}
    ISRSSHUB -->|是| HASBASE{rsshub_base_url?}
    HASBASE -->|是| MERGE[合并 url = base + path]
    HASBASE -->|否| SKIP[返回 None,跳过]
    MERGE --> RSS[RSSSource]
    ISRSSHUB -->|否| RSS
    RSS --> FETCH[fetch since]
    FETCH --> HTTP[httpx.get feed_url]
    HTTP --> PARSE[feedparser.parse]
    PARSE --> ENTRY{每条 entry}
    ENTRY --> DATE[_parse_date<br/>published_parsed → parsedate_to_datetime → 补 UTC]
    DATE -->|>= since| ITEM[ContentItem]
    DATE -->|< since 或 None| SKIP2[跳过]
    ITEM --> LIST[items.append]
```
