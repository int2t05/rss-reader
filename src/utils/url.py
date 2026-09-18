"""URL 规范化:去 fragment/追踪参数,统一协议,小写 host,用于跨源去重。"""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# 追踪参数前缀/全名,去重时一律丢弃
_TRACKING_PARAM_PREFIXES = ("utm_", "ref_", "source_", "spm_", "scm_")
_TRACKING_PARAMS = {
    "ref", "source", "tracking_source", "mc_cid", "mc_eid",
    "fbclid", "gclid", "msclkid", "yclid", "igshid", "spm", "scm",
}


def _is_tracking_param(name: str) -> bool:
    """判断参数是否为追踪参数(utm_* 前缀或已知追踪参数名)。"""
    lower = name.lower()
    if lower in _TRACKING_PARAMS:
        return True
    return any(lower.startswith(prefix) for prefix in _TRACKING_PARAM_PREFIXES)


def normalize_url(url: str) -> str:
    """规范化 URL:去 fragment、追踪参数,统一 https,小写 host,去尾斜杠。

    示例:
        normalize_url("https://Example.com/post/?utm_source=x#frag")
        → "https://example.com/post"
    """
    parts = urlsplit(url.strip())

    # 协议统一为 https
    scheme = "https"

    # host 小写化
    netloc = parts.netloc.lower()

    # 路径去尾斜杠(根路径除外)
    path = parts.path
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    # query 过滤追踪参数
    kept = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not _is_tracking_param(k)]
    query = urlencode(kept)

    # fragment 一律丢弃
    return urlunsplit((scheme, netloc, path, query, ""))
