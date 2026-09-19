# TODO

## 当前不足

| 编号 | 位置 | 问题 | 严重度 |
|---|---|---|---|
| F1 | `src/processing/categories.py` | `parse_category_config` 已提取共享,但 `CategoryRegistry` 与 `Config` 仍各自维护分类列表(两份内存) | Optional |
| F2 | `feeds/*.yml` | 部分 RSSHub 路由源(B 站/Solidot/V2EX 等)需配 `RSSHUB_BASE_URL`,未配时静默跳过 | Optional |
| F3 | `feeds/research.yml` | Papers with Code 暂无官方 RSS,`papers-other` 由期刊会议源填充 | Optional |

## 未来方向

### 功能增强

- **全文抽取**:`content_extractor` 字段已定义,接入 trafilatura 全文提取(当前仅用 RSS summary)
- **Email 发布**:SMTP/IMAP 输出渠道
- **钉钉 Webhook**:新增 `dingtalk` 类型
- **跨日趋势**:SQLite FTS5 全文检索历史简报,识别跨日热点

### 工程优化

- **配置去重**:统一 `CategoryRegistry` 与 `Config` 的分类加载(消除 F1)
- **RSSHub 健康检查**:CI 中探测 `RSSHUB_BASE_URL` 可用性,失败告警
- **主题去重缓存**:LLM 主题去重结果缓存(同标题不重复调用)

### 前端

- **Chirpy 自定义**:首页改为日报卡片墙(替代默认文章列表)
- **搜索增强**:Chirpy 内置 lunr 搜索 + 分类筛选
- **暗色默认**:根据系统偏好自动切换

## 汇总

| 严重度 | 数量 |
|---|---|
| Optional | 3(F1/F2/F3) |
| **总计** | **3** |
