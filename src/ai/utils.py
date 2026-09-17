"""AI 响应解析工具:从 LLM 文本响应中提取 JSON 对象,容忍代码块包裹与前后说明文字。"""

from __future__ import annotations

import json
import re
from typing import Any

# 匹配 ```json ... ``` 代码块
_CODE_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
# 匹配裸 JSON 对象(从首个 { 到匹配的 })
# TODO: 贪婪匹配 \{.*\} 在多 JSON 对象响应中会吞掉中间内容,应用括号配对算法
_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def parse_json_response(response: str) -> dict[str, Any] | None:
    """从 LLM 响应中提取 JSON 对象,多策略容忍代码块/前后文字。

    返回 dict,非对象(如数组)返回 None。无法解析返回 None。

    示例:
        parse_json_response('```json\\n{"a": 1}\\n```') → {"a": 1}
    """
    if not response or not response.strip():
        return None

    # 策略 1:```json 代码块
    code_block = _CODE_BLOCK_RE.search(response)
    if code_block:
        parsed = _try_parse(code_block.group(1))
        if isinstance(parsed, dict):
            return parsed

    # 策略 2:直接解析整段(若整段就是合法 JSON)
    parsed = _try_parse(response.strip())
    if isinstance(parsed, dict):
        return parsed

    # 策略 3:提取首个 {...} 子串
    match = _JSON_OBJECT_RE.search(response)
    if match:
        parsed = _try_parse(match.group(0))
        if isinstance(parsed, dict):
            return parsed

    return None


def _try_parse(text: str) -> Any:
    """尝试 json.loads,失败返回 None。"""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
