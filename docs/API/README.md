# API

rss-reader 是批处理 CLI,无 HTTP 服务。API 文档化 CLI 接口、配置 schema、数据模型。

## CLI 接口

### 完整 pipeline(默认)

```bash
uv run rss-reader --hours 24
```

抓取 → Tier1 → Tier2 → Tier3 → 渲染 → 落盘 → 发布。

### 分阶段

| 命令 | 说明 | 关键参数 |
|---|---|---|
| `--check-config` | 验证配置,输出分类树与源数量 | - |
| `--fetch-only` | 仅抓取,输出每源条目数 | `--hours N` |
| `--classify-only` | Tier1 分类+打分 | `--hours N`, `--limit N` |
| `--select-only` | Tier1 + Tier2 选取 | `--hours N`, `--limit N` |
| `--analyze-one ID` | Tier3 单条深度分析 | `--hours N`,ID 支持前缀/子串匹配 |
| `--no-publish` | 跳过发布,仅落盘 | 与默认 pipeline 合用 |

### 全局参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `--hours N` | 24 | 抓取最近 N 小时 |
| `-d, --data-dir PATH` | `data` | 数据目录(取 parent 作为 project_dir) |
| `-c, --config PATH` | - | 已定义,未实现(见 TODO) |
| `-l, --log-level LEVEL` | WARNING | DEBUG/INFO/WARNING/ERROR/CRITICAL |
| `--limit N` | - | 限制处理条目数(调试) |

### 退出码

- `0`:成功
- `1`:配置错误或未找到 item

## 配置 schema

### `data/config.json`

```jsonc
{
  "ai": {
    "provider": "openai",              // OpenAI 兼容 provider
    "model": "gpt-4o-mini",
    "api_key_env": "OPENAI_API_KEY",   // 环境变量名(非 key 本身)
    "base_url": null,                  // 非 OpenAI 时填
    "analysis_concurrency": 5,         // Tier1 并发
    "throttle_sec": 0.0                // 已定义,未消费(见 TODO)
  },
  "rsshub_base_url": null,             // 未配置时跳过 RSSHub 路由源
  "categories": {
    "<cat-name>": {
      "enabled": true,
      "display_name": {"en": "...", "zh": "..."},
      "threshold": 7.0,
      "digest_limit": 8,
      "children": ["sub1", "sub2"]
    }
  },
  "outputs": {
    "github_pages": true,
    "email": {"enabled": false},       // 已定义,未实现(见 TODO)
    "webhook": [                        // Webhook 列表
      {"type": "feishu", "url": "https://..."},
      {"type": "slack", "url": "https://..."}
    ]
  }
}
```

### `feeds/*.yml`

```yaml
- name: Anthropic News                # 必填
  url: https://...rss.xml             # 必填,支持 ${VAR}
  category: ai-research/ai-vendor     # 必填,分类路径
  enabled: true                       # 可选,默认 true
  content_extractor: null             # 可选,已定义未消费(见 TODO)
```

URL 以 `/` 开头时走 RSSHub 路由(需 `rsshub_base_url`)。

### `categories/<cat>/category.json`

```json
{
  "enabled": true,
  "display_name": {"en": "AI Research", "zh": "AI 研究"},
  "threshold": 7.0,
  "digest_limit": 8,
  "children": ["ai-vendor", "ai-researcher", "ai-papers"]
}
```

## 数据模型

### ContentItem

```python
class ContentItem:
    id: str                              # "rss_<feed_id>_<entry_hash>"
    source_type: SourceType               # RSS | API
    title: str
    url: str
    content: str
    author: str
    published_at: datetime
    category: str | None                 # 源级 category hint
    metadata: dict                       # {feed_name, category, tags}
    processing: ItemProcessing | None
```

### ItemProcessing

```python
class ItemProcessing:
    analysis: ContentAnalysis | None      # Tier1 输出
    deep_analysis: AnalysisResult | None  # Tier3 输出
```

### ContentAnalysis(Tier1)

```python
class ContentAnalysis:
    category_path: str                    # "ai-research/ai-papers"
    score: float                           # 0-10
    summary: str                           # 一句话摘要
    tags: list[str]
    reason: str | None
```

### AnalysisResult(Tier3)

```python
class AnalysisResult:
    title: str
    summary: str                           # 3-5 句总结
    background: str                        # 技术背景
    impact: str                            # 影响与意义
    references: list[Reference]           # 参考链接
    tags: list[str]

class Reference:
    title: str
    url: str
```

### CategoryConfig

```python
class CategoryConfig:
    name: str
    enabled: bool
    display_name: dict[str, str]          # {"en": "...", "zh": "..."}
    threshold: float
    digest_limit: int
    children: list[str]
```

## 环境变量

| 变量 | 必填 | 说明 |
|---|---|---|
| `OPENAI_API_KEY` | 是 | LLM API key |
| `OPENAI_BASE_URL` | 否 | 非 OpenAI provider 端点 |
| `OPENAI_MODEL` | 否 | 覆盖 config 中的 model |
| `EXA_API_KEY` | 否 | Exa 语义搜索(无则降级 DuckDuckGo) |
| `FIRECRAWL_API_KEY` | 否 | Firecrawl JS 渲染抓取(无则降级 trafilatura) |
| `RSSHUB_BASE_URL` | 否 | RSSHub 实例 URL |
| `FLUXSIFT_FEED_URL` | 否 | FluxSift RSS 地址 |
| `FLUXSIFT_TOKEN` | 否 | FluxSift feed token |
| `AUTOTREND_FEED_URL` | 否 | auto-trend RSS 地址 |

## Webhook 类型

| type | payload 格式 | 说明 |
|---|---|---|
| `feishu` | `{"msg_type": "text", "content": {"text": ...}}` | 飞书/Lark |
| `slack` | `{"text": ...}` | Slack |
| `discord` | `{"content": ...}` | Discord |
| `custom` | `{"content": ...}` | 自定义(直接 POST JSON) |
