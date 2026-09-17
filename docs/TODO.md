# TODO

代码 ↔ TODO.md 双向校验:每条 TODO 对应代码中的 `# TODO` 注释,代码中无遗漏 TODO。

---

## 安全 — SSRF 防护

| 编号 | 位置 | 问题 | 严重度 |
|---|---|---|---|
| S1 | `src/ai/agent/ssrf.py:20` | 缺 IPv6 阻断(`::1/128` 回环、`fc00::/7` 唯一本地、`fe80::/10` 链路本地),`http://[::1]/` 可绕过 | Critical |
| S2 | `src/ai/agent/ssrf.py:51` | DNS Rebinding(TOCTOU):验证时解析的 IP 与 httpx 实际请求时的 IP 可能不一致 | Critical |
| S3 | `src/ai/agent/ssrf.py:52` | `socket.gethostbyname` 仅返回 IPv4,IPv6-only 主机被误拒 | Required |
| S4 | `src/ai/agent/fetch_chain.py:121` | 仅验证入口 URL,后端 `follow_redirects=True` 的重定向目标不经 SSRF 校验,302 可绕过 | Critical |

## Agent 层 — ReAct 循环

| 编号 | 位置 | 问题 | 严重度 |
|---|---|---|---|
| A1 | `src/ai/agent/loop.py:148` | 多轮对话压平为单条 user prompt,削弱 ReAct;`AIClient.complete` 应支持多消息对话 | Required |
| A2 | `src/ai/agent/loop.py:176` | 每步仅解析首个工具调用,LLM 多工具调用时丢弃其余 | Required |
| A3 | `src/ai/agent/loop.py:52` | 缺 per-tool-type 计数器(prompt 声明每轮 6 次搜索/8 次抓取,代码未实现) | Required |
| A4 | `src/ai/agent/loop.py:129` | fallback 仅拼接 user 消息,丢弃 assistant 历史,LLM 看不到自己之前的分析 | Required |
| A5 | `src/ai/agent/tool.py:37` | `SyncTool` Protocol 全项目从未使用(工具类直接实现 info+call),应删除或重命名 | Optional |

## AI 客户端与解析

| 编号 | 位置 | 问题 | 严重度 |
|---|---|---|---|
| C1 | `src/ai/client.py:44` | `AIClientConfig.throttle_sec` 从未消费,应实现节流或从配置删除 | Required |
| C2 | `src/ai/client.py:45` | `AsyncOpenAI` 未传 `timeout` 参数,默认 600s,Tier1 批量场景慢请求阻塞 semaphore | Required |
| C3 | `src/ai/utils.py:12` | 贪婪匹配 `\{.*\}` 在多 JSON 对象响应中吞掉中间内容,应用括号配对算法 | Required |
| C4 | `src/ai/selector.py:125` | `parse_json_response` 仅返回 dict,主题去重期望 list,此处为 workaround | Required |

## Source 层

| 编号 | 位置 | 问题 | 严重度 |
|---|---|---|---|
| P1 | `src/sources/rss.py:75` | `entry.get("tags", [])` 对 None 不安全,tags=None 时抛 TypeError 跳过整源 | Required |
| P2 | `src/sources/rss.py:123` | id/link 都缺失时 `entry_id=""`,产生固定哈希,多条目碰撞丢数据 | Required |
| P3 | `src/sources/rss.py:126` | `feed_id` 提取脆弱,`localhost:5000` 含冒号,RSSHub base_url 变更导致去重失效 | Optional |

## 配置加载

| 编号 | 位置 | 问题 | 严重度 |
|---|---|---|---|
| F1 | `src/config.py:22` | `_expand_env` 与 `sources/rss.py` 重复,应提取到 `utils/env.py` 共享 | Required |
| F2 | `src/config.py:96` | `entry["name"]/entry["url"]/entry["category"]` 缺字段时抛 KeyError 中断全部加载 | Required |
| F3 | `src/config.py:138` | `rsshub_base_url` 未做 `${VAR}` 展开,依赖 rss.py 二次展开,隐式依赖 | Required |
| F4 | `src/processing/categories.py:6` | `categories/<cat>/` 目录缺 `analysis.md` 与 `agent_system.md`,生产环境 prompt 返回 None | Required |
| F5 | `src/processing/categories.py:8` | `load_from_raw` 与 `config.py _load_category_configs` 逻辑重复,同一份配置解析两次 | Optional |

## 编排与 CLI

| 编号 | 位置 | 问题 | 严重度 |
|---|---|---|---|
| O1 | `src/main.py:156` | 顺序抓取,70+ 源总耗时为各源之和,应改 `asyncio.gather` 并发 | Required |
| O2 | `src/main.py:366` | 编排逻辑内联在 CLI 入口,应抽取到 `src/orchestrator.py`(CLAUDE.md 结构声明) | Required |
| O3 | `src/main.py:483` | `--data-dir` 参数应改名为 `--project-dir` 以匹配实际语义 | Required |
| O4 | `src/main.py:484` | `--config` 参数已定义但未实现(`args.config` 从未读取) | Required |

## 渲染与发布

| 编号 | 位置 | 问题 | 严重度 |
|---|---|---|---|
| R1 | `src/render/markdown.py:99` | title/url 未转义 Markdown 特殊字符(`]`、`)`),含特殊字符破坏链接语法 | Required |
| R2 | `src/publish/pages.py:41` | `lstrip("# ")` 按字符集剥离,会吃掉 `#hashtag` 中的 `#` | Required |
| R3 | `src/publish/pages.py:44` | title 含双引号破坏 YAML front matter,Jekyll 解析失败 | Required |
| R4 | `src/publish/webhook.py:107` | 顺序执行,与 docstring 声称的"并发"矛盾,应改 `asyncio.gather` | Required |
| R5 | `src/publish/webhook.py:108` | `httpx.AsyncClient` 缺 `trust_env=False`,违反项目约定 | Required |

## 存储与去重

| 编号 | 位置 | 问题 | 严重度 |
|---|---|---|---|
| D1 | `src/storage/dedup.py:22` | 未设 WAL 模式,并发写抛 `database is locked` | Required |
| D2 | `src/storage/dedup.py:23` | 未设 `check_same_thread=False`,async 场景跨线程使用会抛错 | Required |

## URL 规范化

| 编号 | 位置 | 问题 | 严重度 |
|---|---|---|---|
| U1 | `src/utils/url.py:8` | 未覆盖 `fbclid`/`gclid`/`msclkid`/`yclid`/`igshid`/`spm`/`scm` 等常见追踪参数 | Required |

## 数据源配置

| 编号 | 位置 | 问题 | 严重度 |
|---|---|---|---|
| E1 | `feeds/research.yml:47` | Papers with Code 暂无官方 RSS,`papers-other` 子类预留无源 | Optional |

---

## 汇总

| 严重度 | 数量 |
|---|---|
| Critical | 4(S1/S2/S4 + S2 重定向) |
| Required | 24 |
| Optional | 4 |
| **总计** | **32** |

## 修复优先级

1. **立即修复(Critical)**:SSRF 三漏洞(S1/S2/S4)— IPv6 阻断 + DNS Rebinding + 重定向校验
2. **近期修复(Required,安全/数据完整性)**:P1/P2(条目丢数据)、F2(配置加载中断)、D1/D2(并发写)
3. **中期改进(Required,性能/正确性)**:O1(并发抓取)、A1-A4(agent 循环质量)、C1-C3(AI 客户端)
4. **长期重构(Required,架构)**:O2(抽取 orchestrator)、F1/F5(去重复)、R1-R3(渲染发布)
5. **可选清理(Optional)**:A5/F5/E1
