# FLOW

## 完整 pipeline

```mermaid
flowchart TB
    START([uv run rss-reader --hours 24]) --> LOAD[load_config<br/>data/config.json + feeds/*.yml + categories/*]
    LOAD --> FETCH[_fetch_all_items<br/>顺序抓取所有源]
    FETCH --> T1[ContentClassifier.classify_batch<br/>Tier1: 单次 LLM 分类+打分]
    T1 --> T2[ContentSelector.select<br/>Tier2: 选取+去重]
    T2 --> T3[Tier3: AgentLoop 循环]
    T3 --> RND[render_bilingual<br/>中英双语]
    RND --> SUM[SummaryStore.save_bilingual<br/>data/summaries/]
    RND --> PUB[_publish<br/>Pages + Webhook]
    PUB --> DONE([Pipeline complete])
```

## Tier 1:分类 + 打分

```mermaid
flowchart LR
    ITEMS[list[ContentItem]<br/>200-500 条] --> BATCH[classify_batch<br/>Semaphore 并发]
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

**并发**:`analysis_concurrency` Semaphore(默认 5),单条失败写入默认 analysis 不中断。

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

## Tier 3:Agent 循环

```mermaid
flowchart TB
    ITEM[精选 ContentItem] --> CRAG[CRAGEvaluator.evaluate]
    CRAG -->|strong| SKIP[跳过联网<br/>system prompt 追加指引]
    CRAG -->|ambiguous| AUTO[agent 自主决策]
    CRAG -->|weak| FORCE[强制先 web_search]
    SKIP --> LOOP[ReAct 循环 max 10 步]
    AUTO --> LOOP
    FORCE --> LOOP

    LOOP --> CALL[_call_llm_with_tools<br/>system + 合并 user prompt]
    CALL --> PARSE[_parse_tool_calls]
    PARSE -->|有工具调用| EXEC[执行工具]
    PARSE -->|无工具调用| JSON[解析最终 JSON]
    EXEC --> SCH{web_search?}
    SCH -->|是| SEARCH[SearchChain<br/>Exa → DuckDuckGo]
    SCH -->|否| FETCH[web_fetch?]
    FETCH -->|是| FCH[FetchChain<br/>Firecrawl → trafilatura → httpx]
    FCH --> SSRF[validate_url<br/>SSRF 防护]
    FETCH -->|否| TOOL_RESULT[工具结果]
    SEARCH --> TOOL_RESULT
    SSRF --> TOOL_RESULT
    TOOL_RESULT --> APPEND[追加到 messages]
    APPEND --> NEXT{步数 < 10?}
    NEXT -->|是| LOOP
    NEXT -->|否| FALL[fallback AnalysisResult]

    JSON --> RESULT[AnalysisResult<br/>title/summary/background/impact/references/tags]
    RESULT --> DONE[item.processing.deep_analysis = result]
    FALL --> DONE
```

**数据**:输入 `ContentItem`(带 analysis),输出 `AnalysisResult`(原地写入 `item.processing.deep_analysis`)。

**工具调用格式**:LLM 在响应中用 ` ```tool\n<name>\n<args>\n``` ` 或 `web_search("query")` 格式声明工具调用。

## 降级链

### SearchChain

```mermaid
flowchart LR
    Q[query] --> EXA{EXA_API_KEY?}
    EXA -->|是| EXAC[ExaClient<br/>api.exa.ai/search]
    EXA -->|否| DDG[DuckDuckGoClient<br/>ddgs 库]
    EXAC -->|成功非空| RET[返回结果]
    EXAC -->|失败/空| DDG
    DDG -->|成功非空| RET
    DDG -->|失败| EMPTY[返回空列表]
```

### FetchChain

```mermaid
flowchart LR
    URL --> V[validate_url<br/>SSRF 防护]
    V --> FC{FIRECRAWL_API_KEY?}
    FC -->|是| FCC[FirecrawlClient<br/>JS 渲染]
    FC -->|否| TRA[TrafilaturaClient]
    FCC -->|成功非空| RET[返回 Markdown]
    FCC -->|失败/空| TRA
    TRA -->|成功非空| RET
    TRA -->|失败/空| HTTP[LocalHttpClient<br/>httpx + 正则]
    HTTP -->|成功非空| RET
    HTTP -->|失败| EMPTY[返回空字符串]
```

## 双语渲染 + 发布

```mermaid
flowchart LR
    ITEMS[带 analysis + deep_analysis 的 items] --> ZH[render_markdown<br/>lang=zh]
    ITEMS --> EN[render_markdown<br/>lang=en]
    ZH --> BR[BilingualResult<br/>.zh + .en]
    EN --> BR
    BR --> SUM[SummaryStore.save_bilingual<br/>data/summaries/YYYY-MM-DD-{zh,en}.md]
    BR --> PAGES[GitHubPagesPublisher<br/>docs/_posts/YYYY-MM-DD-{zh,en}.md<br/>Jekyll front matter]
    BR --> HOOK{webhook 配置?}
    HOOK -->|是| WH[WebhookPublisher<br/>Feishu/Slack/Discord/Custom]
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
