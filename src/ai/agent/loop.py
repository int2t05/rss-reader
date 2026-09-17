"""AgentLoop:Tier3 有界 ReAct 循环,借鉴 Cognik loop.go 翻译为 Python。

max_steps=10 硬上限。CRAG 入口评估:strong 跳过联网 / ambiguous 自主 / weak 强制。
工具:web_search(SearchChain) + web_fetch(FetchChain)。非流式调用。
输出结构化 JSON:{title, summary, background, impact, references, tags}。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.ai.agent.crag import CRAGEvaluator
from src.ai.agent.fetch_chain import FetchChain
from src.ai.agent.search_chain import SearchChain
from src.ai.agent.tool import ToolInfo, ToolRegistry
from src.ai.client import AIClient
from src.ai.prompting.agent_system import (
    agent_system_prompt,
    fallback_result_prompt,
)
from src.ai.utils import parse_json_response
from src.models import AnalysisResult, ContentItem, Reference

logger = logging.getLogger(__name__)


class AgentLoop:
    """有界 ReAct 循环:max_steps 硬上限,CRAG 评估入口,工具调用降级链。

    示例:
        loop = AgentLoop(client, registry, crag, search_chain, fetch_chain, max_steps=10)
        result = await loop.run(item, category_display_name="AI 研究")
    """

    def __init__(
        self,
        client: AIClient,
        registry: ToolRegistry,
        crag: CRAGEvaluator,
        search_chain: SearchChain,
        fetch_chain: FetchChain,
        max_steps: int = 10,
    ):
        self.client = client
        self.registry = registry
        self.crag = crag
        self.search_chain = search_chain
        self.fetch_chain = fetch_chain
        self.max_steps = max_steps
        # TODO: 缺 per-tool-type 计数器(prompt 声明每轮 6 次搜索/8 次抓取,代码未实现)
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """注册内置工具:web_search + web_fetch。"""
        self.registry.register(_WebSearchTool(self.search_chain))
        self.registry.register(_WebFetchTool(self.fetch_chain))

    async def run(self, item: ContentItem, category_display_name: str) -> AnalysisResult:
        """运行 Tier3 深度分析:CRAG 评估 → ReAct 循环 → 结构化 JSON 输出。

        max_steps 超步返回 fallback AnalysisResult(title=item.title, summary=Tier1 summary)。
        """
        verdict = self.crag.evaluate(item)
        system_prompt = agent_system_prompt(
            category=item.category or "unknown",
            display_name=category_display_name,
        )
        if verdict == "strong":
            system_prompt += "\n\n[CRAG=strong] 内容已充分,直接输出总结 JSON,不要调用工具。"
        elif verdict == "weak":
            system_prompt += "\n\n[CRAG=weak] 内容不足,必须先调用 web_search 补充背景。"
        else:
            system_prompt += "\n\n[CRAG=ambiguous] 内容中等,自主决定是否调用 web_search。"

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"标题:{item.title}\n"
                    f"内容:{item.content[:3000]}\n"
                    f"URL:{item.url}\n"
                    f"来源:{item.metadata.get('feed_name', 'Unknown')}"
                ),
            },
        ]

        for step in range(self.max_steps):
            try:
                response = await self._call_llm_with_tools(messages)
            except Exception as e:
                logger.warning("Agent loop step %d failed for %s: %s", step, item.id, e)
                return self._fallback_result(item)

            messages.append({"role": "assistant", "content": response})

            tool_calls = self._parse_tool_calls(response)
            if not tool_calls:
                # LLM 输出最终 JSON,尝试解析
                result = self._parse_analysis_result(response, item)
                if result is not None:
                    return result
                # JSON 解析失败,追加修复提示继续
                messages.append(
                    {
                        "role": "user",
                        "content": "你上次的响应不是合法 JSON。请仅输出包含 title/summary/background/impact/references/tags 的 JSON 对象。",
                    }
                )
                continue

            # 执行工具调用
            for tc in tool_calls:
                tool_result = await self._execute_tool(tc)
                messages.append(
                    {
                        "role": "user",
                        "content": f"[tool_result for {tc['name']}] {tool_result}",
                    }
                )

        # 超步 fallback
        logger.warning("Agent loop exceeded max_steps=%d for %s, returning fallback", self.max_steps, item.id)
        # 最后尝试一次让 LLM 输出最小 JSON
        try:
            messages.append({"role": "user", "content": fallback_result_prompt()})
            # TODO: fallback 仅拼接 user 消息,丢弃 assistant 历史,LLM 看不到自己之前的分析
            response = await self.client.complete(
                system=system_prompt,
                user="\n\n".join(m["content"] for m in messages if m["role"] == "user"),
                temperature=0,
            )
            result = self._parse_analysis_result(response, item)
            if result is not None:
                return result
        except Exception as e:
            logger.warning("Fallback LLM call failed for %s: %s", item.id, e)
        return self._fallback_result(item)

    async def _call_llm_with_tools(self, messages: list[dict[str, Any]]) -> str:
        """调用 LLM,messages 包含 system/user/assistant/tool_result 序列。

        简化实现:不传 tools 参数(部分 OpenAI 兼容端点不支持 function calling),
        而是在 system prompt 中描述工具,LLM 在响应中用特定格式调用工具。
        """
        # TODO: 多轮对话压平为单条 user prompt,削弱 ReAct;AIClient.complete 应支持多消息对话
        # 构建单次 complete 调用:system + 完整 user 序列
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        # 把所有 user/assistant 消息合并为 user prompt
        history_parts = []
        for m in messages:
            if m["role"] == "system":
                continue
            role_label = {"user": "User", "assistant": "Assistant"}.get(m["role"], m["role"])
            history_parts.append(f"[{role_label}]\n{m['content']}")
        user_prompt = "\n\n".join(history_parts) or "分析上述内容。"
        return await self.client.complete(system=system, user=user_prompt)

    def _parse_tool_calls(self, response: str) -> list[dict[str, Any]]:
        """从 LLM 响应中解析工具调用。

        约定格式(LLM 自行输出):
            ```tool
            web_search
            {"query": "OpenAI GPT-5"}
            ```
        或纯文本:
            web_search("OpenAI GPT-5")

        解析失败返回空列表(视为最终 JSON 输出)。
        """
        import re

        # TODO: 当前每步仅解析首个工具调用,LLM 多工具调用时丢弃其余,应支持并行工具调用
        # 模式 1:```tool\n<tool_name>\n<json_args>\n```
        tool_block = re.search(r"```tool\s*\n(\w+)\s*\n(.*?)\n```", response, re.DOTALL)
        if tool_block:
            tool_name = tool_block.group(1)
            args_str = tool_block.group(2).strip()
            try:
                args = json.loads(args_str) if args_str else {}
            except json.JSONDecodeError:
                args = {}
            return [{"name": tool_name, "args": args}]

        # 模式 2:tool_name("query") 或 tool_name({"query": "..."})
        m = re.search(r'(web_search|web_fetch)\s*\(\s*(.*?)\s*\)', response)
        if m:
            tool_name = m.group(1)
            args_str = m.group(2)
            # 尝试 JSON 解析
            try:
                if args_str.startswith("{"):
                    args = json.loads(args_str)
                else:
                    # 去引号,作为 query/url 参数
                    cleaned = args_str.strip("'\"")
                    args = {"query": cleaned} if tool_name == "web_search" else {"url": cleaned}
            except json.JSONDecodeError:
                args = {}
            return [{"name": tool_name, "args": args}]

        return []

    async def _execute_tool(self, tool_call: dict[str, Any]) -> str:
        """执行单个工具调用,返回结果字符串。"""
        tool = self.registry.get(tool_call["name"])
        if tool is None:
            return f"Error: tool {tool_call['name']} not found"
        try:
            result = await tool.call(tool_call["args"])  # type: ignore[attr-defined]
            return result
        except Exception as e:
            return f"Error calling {tool_call['name']}: {e}"

    def _parse_analysis_result(self, response: str, item: ContentItem) -> AnalysisResult | None:
        """从 LLM 响应解析 AnalysisResult,失败返回 None。"""
        parsed = parse_json_response(response)
        if not isinstance(parsed, dict):
            return None
        try:
            title = str(parsed.get("title", "") or item.title)
            summary = str(parsed.get("summary", "") or "")
            if not summary:
                return None
            background = str(parsed.get("background", "") or "")
            impact = str(parsed.get("impact", "") or "")
            refs_raw = parsed.get("references", []) or []
            references = []
            for r in refs_raw:
                if isinstance(r, dict) and r.get("url"):
                    references.append(Reference(title=str(r.get("title", "")), url=str(r["url"])))
            tags = list(parsed.get("tags", []) or [])
            return AnalysisResult(
                title=title,
                summary=summary,
                background=background,
                impact=impact,
                references=references,
                tags=tags,
            )
        except (TypeError, ValueError) as e:
            logger.warning("AnalysisResult parse error: %s", e)
            return None

    def _fallback_result(self, item: ContentItem) -> AnalysisResult:
        """构造 fallback AnalysisResult:使用 item.title 与 Tier1 summary。"""
        summary = ""
        if item.processing and item.processing.analysis:
            summary = item.processing.analysis.summary or item.title
        if not summary:
            summary = item.title
        return AnalysisResult(title=item.title, summary=summary)


class _WebSearchTool:
    """web_search 工具:调用 SearchChain 返回搜索结果 JSON。"""

    def __init__(self, search_chain: SearchChain):
        self._chain = search_chain

    def info(self) -> ToolInfo:
        return ToolInfo(
            name="web_search",
            description="Search the web. Returns JSON list of {title, url, snippet}.",
            parameters={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        )

    async def call(self, args: dict[str, Any]) -> str:
        query = args.get("query", "")
        if not query:
            return "Error: query is required"
        results = await self._chain.search(query, max_results=5)
        return json.dumps(
            [{"title": r.title, "url": r.url, "snippet": r.snippet} for r in results],
            ensure_ascii=False,
        )


class _WebFetchTool:
    """web_fetch 工具:调用 FetchChain 返回网页正文(截断)。"""

    def __init__(self, fetch_chain: FetchChain):
        self._chain = fetch_chain

    def info(self) -> ToolInfo:
        return ToolInfo(
            name="web_fetch",
            description="Fetch a web page and return its main content as Markdown.",
            parameters={
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        )

    async def call(self, args: dict[str, Any]) -> str:
        url = args.get("url", "")
        if not url:
            return "Error: url is required"
        content = await self._chain.fetch(url)
        return content[:12000] if content else "(empty content)"
