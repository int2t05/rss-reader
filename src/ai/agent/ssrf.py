"""SSRF 防护:web_fetch 工具调用前验证 URL,拒绝 localhost/内网/云元数据端点。

借鉴 Cognik server/internal/infra/adapter/fetch_client.go:66-97 的 validateURL。
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

# 阻断的网络段:localhost、私有网络、云元数据、保留地址
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),       # loopback
    ipaddress.ip_network("10.0.0.0/8"),        # 私有网络 A
    ipaddress.ip_network("172.16.0.0/12"),     # 私有网络 B
    ipaddress.ip_network("192.168.0.0/16"),    # 私有网络 C
    ipaddress.ip_network("169.254.0.0/16"),    # 链路本地 + 云元数据
    ipaddress.ip_network("0.0.0.0/8"),         # 保留
    # TODO: 缺 IPv6 阻断(::1/128 回环、fc00::/7 唯一本地、fe80::/10 链路本地),可绕过 SSRF
]


class ValidationError(Exception):
    """URL 验证失败异常。"""


def validate_url(url: str) -> None:
    """验证 URL,拒绝 localhost/内网/云元数据/非 HTTP 协议。

    示例:
        validate_url("https://example.com/post")  # 通过
        validate_url("http://127.0.0.1/admin")   # 抛 ValidationError
    """
    if not url or not url.strip():
        raise ValidationError("Empty URL")

    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise ValidationError(f"Blocked scheme: {parsed.scheme or '(none)'}")

    hostname = parsed.hostname
    if not hostname:
        raise ValidationError("No hostname in URL")

    # 拒绝 localhost 主机名
    if hostname.lower() in ("localhost",):
        raise ValidationError(f"Blocked localhost: {hostname}")

    # 解析 IP 地址(若 hostname 是域名,解析后检查)
    # TODO: 存在 DNS Rebinding(TOCTOU)漏洞:验证时解析的 IP 与 httpx 实际请求时的 IP 可能不一致
    # TODO: socket.gethostbyname 仅返回 IPv4,IPv6-only 主机会被误拒
    try:
        # 优先按 IP 字面量解析
        try:
            ip = ipaddress.ip_address(hostname)
        except ValueError:
            # 域名:DNS 解析后检查(同步 socket.gethostbyname)
            resolved = socket.gethostbyname(hostname)
            ip = ipaddress.ip_address(resolved)
    except (socket.gaierror, ValueError) as e:
        raise ValidationError(f"Cannot resolve hostname: {hostname}") from e

    for network in _BLOCKED_NETWORKS:
        if ip in network:
            raise ValidationError(f"Blocked internal IP: {ip}")
