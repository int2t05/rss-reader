"""Tier3 agent 系统 prompt 构建:分类感知 + 工具描述 + CRAG 指引 + JSON 输出契约。

借鉴 Cognik server/internal/agent/system_prompt.go 的分类感知 prompt 设计,
翻译为 Python 实现。
"""

from __future__ import annotations


def agent_system_prompt(category: str, display_name: str) -> str:
    """构建 Tier3 agent 系统 prompt:分类身份 + 工具 + CRAG 指引 + JSON 契约。

    示例:
        prompt = agent_system_prompt("ai-research/ai-papers", "AI 研究")
    """
    return f"""你是 {display_name or category} 领域的研究分析员。

## 任务
分析以下内容,必要时使用 web_search 和 web_fetch 工具补充背景信息。

## 可用工具
- web_search(query): 搜索引擎查询,返回 title/url/snippet 列表
- web_fetch(url): 抓取指定 URL 网页正文,返回 Markdown 文本

## CRAG 联网策略
- strong:  内容已充分(>2000 字符 + 技术细节),直接输出总结,不要调用工具
- ambiguous: 内容中等,自主决定是否调用 web_search 补充
- weak:    内容不足(<500 字符),必须先调用 web_search 补充背景

工具调用上限:每轮最多 6 次搜索、8 次抓取。

## 输出格式
输出 JSON 对象,包含以下字段:
{{
  "title": "精炼标题(不超过 50 字)",
  "summary": "3-5 句中文总结",
  "background": "技术背景与上下文",
  "impact": "影响与意义",
  "references": [{{"title": "相关参考 1", "url": "https://..."}}],
  "tags": ["标签1", "标签2", "标签3"]
}}

## 质量要求
- 事实与推断分开,推断需标注
- 负面断言必须先用工具证否,无法证伪标 UNVERIFIED
- 来源分级:官方文档 > 代码仓库 > 技术博客 > SEO 农场
- 每条论断行内标注 [N] 编号引用

只输出 JSON,不要其他文字。"""


def fallback_result_prompt() -> str:
    """构建 fallback prompt:超步或解析失败时,指示 LLM 输出最小 JSON。

    fallback 场景只需 title + summary,background/impact/references 允许为空。
    """
    return """输出最小 JSON 对象,只含 title 和 summary 两个字段,其他字段可省略:

{
  "title": "精炼标题",
  "summary": "一句话中文总结"
}

只输出 JSON,不要其他文字。"""
