"""CRAG 充分性评估器:根据内容长度与技术细节判定 strong/ambiguous/weak。

借鉴 Cognik server/internal/rag/crag.go 的 ThresholdEvaluator,简化为内容启发式:
- strong:   内容 > 2000 字符 且 含技术细节(代码/API/版本号)→ 跳过联网
- ambiguous: 内容 500-2000 字符,或长内容无技术细节 → agent 自主决策
- weak:     内容 < 500 字符 → 强制联网
"""

from __future__ import annotations

import re

from src.models import ContentItem

# 技术细节标记:代码块、函数定义、API/协议关键词、版本号
_TECHNICAL_PATTERNS = [
    r"```",                       # 代码块
    r"\bdef\s+\w+\s*\(",          # Python 函数定义
    r"\bclass\s+\w+\s*[:\(]",     # Python/JS 类定义
    r"\bfunction\s+\w+\s*\(",     # JS 函数定义
    r"\b(API|HTTP|HTTPS|GPU|CPU|CUDA|LLM|GPT|Transformer)\b",
    r"\b\d+\.\d+\.\d+\b",         # 版本号 x.y.z
    r"\b\d+\.\d+\b",              # 版本号 x.y
]
_TECHNICAL_RE = re.compile("|".join(_TECHNICAL_PATTERNS))

_STRONG_MIN_CHARS = 2000
_WEAK_MAX_CHARS = 500


class CRAGEvaluator:
    """充分性评估器:决定 agent 是否需要联网补充。

    示例:
        evaluator = CRAGEvaluator()
        verdict = evaluator.evaluate(item)
        # verdict ∈ {"strong", "ambiguous", "weak"}
    """

    def evaluate(self, item: ContentItem) -> str:
        """返回 strong / ambiguous / weak,决定 agent 联网策略。"""
        content_len = len(item.content)
        if content_len < _WEAK_MAX_CHARS:
            return "weak"
        if content_len > _STRONG_MIN_CHARS and self._has_technical_detail(item.content):
            return "strong"
        return "ambiguous"

    def _has_technical_detail(self, content: str) -> bool:
        """简单启发式:是否包含代码块、函数定义、API 术语或版本号。"""
        return bool(_TECHNICAL_RE.search(content))
