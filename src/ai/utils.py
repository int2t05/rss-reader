"""AI 响应解析工具:从 LLM 文本响应中提取 JSON 对象或数组,容忍代码块包裹与前后说明文字。

用括号配对算法提取(支持嵌套与字符串内的括号),替代贪婪正则,避免多 JSON 对象响应吞掉中间内容。
"""

from __future__ import annotations

import json
import re
from typing import Any

# 匹配 ```json ... ``` 代码块(内容非贪婪,内部 JSON 由括号配对提取)
_CODE_BLOCK_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _extract_balanced(text: str, open_ch: str, close_ch: str) -> str | None:
    """从 text 提取首个括号配对的子串(支持嵌套与字符串内括号),失败返回 None。

    示例:'prefix {"a": {"b": 1}} suffix' → '{"a": {"b": 1}}'
    """
    start = text.find(open_ch)
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _try_parse(text: str) -> Any:
    """尝试 json.loads,失败返回 None。"""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


def parse_json_response(response: str) -> dict[str, Any] | None:
    """从 LLM 响应中提取 JSON 对象,多策略容忍代码块/前后文字。

    返回 dict,非对象(如数组)返回 None。无法解析返回 None。

    示例:
        parse_json_response('```json\\n{"a": 1}\\n```') → {"a": 1}
    """
    if not response or not response.strip():
        return None

    # 优先从 ```json 代码块提取,再回退到整段
    code_block = _CODE_BLOCK_RE.search(response)
    sources = [code_block.group(1)] if code_block else []
    sources.append(response)

    for src in sources:
        obj = _extract_balanced(src, "{", "}")
        if obj is None:
            continue
        parsed = _try_parse(obj)
        if isinstance(parsed, dict):
            return parsed
    return None


def parse_json_array_response(response: str) -> list[Any] | None:
    """从 LLM 响应中提取 JSON 数组,多策略容忍代码块/前后文字。

    返回 list,非数组(如对象)返回 None。无法解析返回 None。

    示例:
        parse_json_array_response('[["id1", "id2"], ["id3"]]') → [["id1", "id2"], ["id3"]]
    """
    if not response or not response.strip():
        return None

    code_block = _CODE_BLOCK_RE.search(response)
    sources = [code_block.group(1)] if code_block else []
    sources.append(response)

    for src in sources:
        arr = _extract_balanced(src, "[", "]")
        if arr is None:
            continue
        parsed = _try_parse(arr)
        if isinstance(parsed, list):
            return parsed
    return None
