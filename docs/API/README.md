# API

rss-reader 是批处理 CLI,无 HTTP 服务。本文档化 CLI 接口、配置 schema、数据模型。

## CLI 接口

### 完整 pipeline(默认)

```bash
uv run rss-reader --hours 24
```

抓取 → Tier1 → Tier2 → 渲染 → 落盘 → 发布。

### 分阶段

| 命令 | 说明 | 关键参数 |
|---|---|---|
| `--check-config` | 验证配置,输出分类树与源数量 | - |
| `--fetch-only` | 仅抓取,输出每源条目数 | `--hours N` |
| `--classify-only` | Tier1 分类+打分+摘要 | `--hours N`, `--limit N` |
| `--select-only` | Tier1 + Tier2 选取 | `--hours N`, `--limit N` |
| `--no-publish` | 跳过发布,仅落盘 | 与默认 pipeline 合用 |

### 全局参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `--hours N` | 24 | 抓取最近 N 小时 |
| `-d, --project-dir PATH` | 当前目录 | 项目根(含 data/、categories/、feeds/) |
| `-c, --config PATH` | `data/config.json` | 自定义 config 路径 |
| `-l, --log-level LEVEL` | WARNING | DEBUG/INFO/WARNING/ERROR/CRITICAL |
| `--limit N` | - | 限制处理条目数(调试) |

### 退出码

- `0`:成功
- `1`:配置错误

## 配置 schema

### `data/config.json`

```jsonc
{
  "ai": {
    "provider": "openai",              // OpenAI 兼容 provider
    "model": "glm-5.2",                // 默认模型(OPENAI_MODEL 环境变量覆盖)
    "api_key_env": "OPENAI_API_KEY",   // 环境变量名(非 key 本身)
    "base_url": null,                  // 非 OpenAI 时填
    "analysis_concurrency": 10         // Tier1 并发
  },
  "rsshub_base_url": null,             // 未配置时跳过 RSSHub 路由源
  "categories": {
    "<cat-name>": {
      "enabled": true,
      "display_name": "中文显示名",
      "threshold": 7.0,
      "digest_limit": 8,
      "children": ["sub1", "sub2"]
    }
  },
  "outputs": {
    "github_pages": true,
    "email": {"enabled": false},
    "webhook": [
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
  content_extractor: null             # 可选,已定义未消费
```

URL 以 `/` 开头时走 RSSHub 路由(需 `rsshub_base_url`)。

### `categories/<cat>/category.json`

```json
{
  "enabled": true,
  "display_name": "AI 研究",
  "threshold": 7.0,
  "digest_limit": 8,
  "children": ["ai-vendor", "ai-researcher", "ai-papers"]
}
```

## 数据模型

### ContentItem

```python
class ContentItem:
    id: str                              # "rss_<source_slug>_<entry_hash>"
    source_type: SourceType               # RSS
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

### CategoryConfig

```python
class CategoryConfig:
    name: str
    enabled: bool
    display_name: str                     # 中文显示名
    threshold: float
    digest_limit: int
    children: list[str]
```

## 环境变量

| 变量 | 必填 | 说明 |
|---|---|---|
| `OPENAI_API_KEY` | 是 | LLM API key |
| `OPENAI_BASE_URL` | 否 | 非 OpenAI provider 端点(火山方舟等) |
| `OPENAI_MODEL` | 否 | 覆盖 config 中的 model |
| `RSSHUB_BASE_URL` | 否 | RSSHub 实例 URL |
| `FLUXSIFT_FEED_URL` | 否 | FluxSift 自建视频源 RSS 地址(含 token,经 cpolar 隧道) |

## Webhook 类型

| type | payload 格式 | 说明 |
|---|---|---|
| `feishu` | `{"msg_type": "text", "content": {"text": ...}}` | 飞书/Lark |
| `slack` | `{"text": ...}` | Slack |
| `discord` | `{"content": ...}` | Discord |
| `custom` | `{"content": ...}` | 自定义(直接 POST JSON) |

## LLM 配置(与 Claude Code 同凭证机制)

本项目用 OpenAI 兼容端点,通过 `.env` 配置(与 Claude Code 读取 `.env` 的机制一致):

```bash
# .env
OPENAI_API_KEY=sk-xxx                    # 火山方舟 API key
OPENAI_BASE_URL=https://...apigateway.../compatible  # OpenAI 兼容端点
OPENAI_MODEL=glm-5.2                     # 模型名(覆盖 config.json 默认 gpt-4o-mini)
```

CI(GitHub Actions)通过 repository secrets 注入同名变量,见 `.github/workflows/daily.yml`。
