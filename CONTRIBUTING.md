# 贡献指南

欢迎参与 rss-reader 开发。

## 开发环境

```bash
git clone <repo-url>
cd rss-reader
uv sync --extra dev
cp .env.example .env  # 填入测试用 API key
```

## 开发流程

1. Fork 仓库,创建分支:`git checkout -b feature/your-feature`
2. 编写代码:遵循现有风格,注释中文简洁解释功能
3. 编写测试:`test/` 目录下,测试名描述行为,无 mock,真实数据
4. 运行测试:`uv run pytest`
5. 提交 PR:关联 issue,描述变更与验证

## 代码风格

- Python 3.12+,类型标注完整
- `httpx.AsyncClient` 必须 `trust_env=False`(避免系统代理干扰)
- 注释中文简洁,解释功能不复述逻辑
- 每个文件头注释一行说明用途
- 每个关键函数注释一行说明功能
- 待完善处加 `# TODO` 注释,与 `docs/TODO.md` 保持一致

## 测试约定

- **无 mock**:真实调用真实数据,网络不可达时 `pytest.skip`
- 测试名描述行为(`test_classify_returns_score`),非实现(`test_1`)
- `@pytest.mark.network`:真实网络抓取
- `@pytest.mark.llm`:真实 LLM 调用,无 key 时 skip

## 分类与源配置

- 新增分类:`categories/<cat>/category.json` + `data/config.json` 声明 + 必要时 `feeds/<cat>.yml`
- 新增 RSS 源:`feeds/<cat>.yml` 加一行,零代码
- 预留分类(财经/加密货币)`enabled: false`,启用零代码

## 提交规范

- commit message 格式:`type(scope): description`
- type:`feat` / `fix` / `docs` / `refactor` / `test` / `chore`
- 示例:`feat(agent): add per-tool-type counter`、`fix(ssrf): block IPv6 loopback`

## Issue 与 PR

- Bug 报告用 bug 模板,Feature 请求用 feature 模板
- PR 关联 issue,描述变更、验证方式、影响范围
