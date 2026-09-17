"""内容分块与采样:split_content 分离正文与评论,select_content 按 max_chars + 策略截取。

借鉴 Horizon src/processing/content.py:RSS 条目正文与社区评论分离,长文本按策略采样。
"""

from __future__ import annotations

from dataclasses import dataclass

_CONTENT_SEPARATOR = "---"


@dataclass
class ContentParts:
    """内容分块结果:main 为正文,comments 为社区评论。"""

    main: str
    comments: str


def split_content(text: str) -> ContentParts:
    """按 --- 分隔符分离正文与评论。

    首个 --- 之前为 main,之后全部为 comments。无分隔符时全部为 main。

    示例:
        parts = split_content("正文\\n---\\n评论")
        # parts.main == "正文", parts.comments == "评论"
    """
    if not text:
        return ContentParts(main="", comments="")
    if _CONTENT_SEPARATOR not in text:
        return ContentParts(main=text, comments="")
    main, _, comments = text.partition(_CONTENT_SEPARATOR)
    return ContentParts(main=main.strip(), comments=comments.strip())


def select_content(text: str, max_chars: int, sampling: str = "head") -> str:
    """按 max_chars 和采样策略截取内容,控制 LLM 输入长度。

    sampling 策略:
        head:      前 max_chars 字符
        tail:      末尾 max_chars 字符
        head_tail: 前半 + 省略 + 后半,总长 ≤ max_chars
    """
    if not text or max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text

    if sampling == "tail":
        return text[-max_chars:]

    if sampling == "head_tail":
        half = max_chars // 2
        ellipsis_len = 5  # "..." 长度
        keep = max(half - ellipsis_len, 1)
        return text[:keep] + "..." + text[-keep:]

    # 默认 head
    return text[:max_chars]
