"""URL 规范化测试:去 fragment/追踪参数/统一协议/小写 host。"""
from src.utils.url import normalize_url


def test_normalize_strips_fragment():
    """去 fragment(#xxx)。"""
    assert normalize_url("https://example.com/post#section") == "https://example.com/post"


def test_normalize_strips_utm_params():
    """去 utm_* 等追踪参数。"""
    url = "https://example.com/post?utm_source=twitter&utm_medium=social&ref=newsletter&id=123"
    assert normalize_url(url) == "https://example.com/post?id=123"


def test_normalize_keeps_non_tracking_params():
    """非追踪参数(id、v)保留。"""
    assert normalize_url("https://example.com/p?id=123&v=2") == "https://example.com/p?id=123&v=2"


def test_normalize_lowercases_hostname():
    """hostname 小写化。"""
    assert normalize_url("HTTPS://Example.COM/Post") == "https://example.com/Post"


def test_normalize_upgrades_http_to_https():
    """http 升级为 https。"""
    assert normalize_url("http://example.com/post") == "https://example.com/post"


def test_normalize_strips_trailing_slash():
    """去除尾斜杠,但保留根路径的斜杠。"""
    assert normalize_url("https://example.com/post/") == "https://example.com/post"
    # 根路径保留斜杠
    assert normalize_url("https://example.com/") == "https://example.com/"


def test_normalize_idempotent():
    """规范化幂等:两次规范化结果一致。"""
    url = "https://example.com/post/?utm_source=x#frag"
    once = normalize_url(url)
    twice = normalize_url(once)
    assert once == twice


def test_normalize_preserves_query_order():
    """非追踪参数顺序保留。"""
    url = "https://example.com/p?b=2&a=1&utm_source=x"
    assert normalize_url(url) == "https://example.com/p?b=2&a=1"


def test_normalize_drops_empty_query():
    """所有参数都是追踪参数时,query 整体丢弃。"""
    url = "https://example.com/p?utm_source=x&utm_medium=y"
    assert normalize_url(url) == "https://example.com/p"
