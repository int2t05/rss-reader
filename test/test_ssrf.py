"""SSRF 防护测试:拒绝 localhost/内网/云元数据 URL,允许公网 HTTP/HTTPS。

纯逻辑测试,无网络无 LLM。
"""
import pytest

from src.ai.agent.ssrf import validate_url, ValidationError


def test_validate_https_public_url():
    """公网 HTTPS URL 通过验证。"""
    validate_url("https://example.com/post")  # 不抛异常


def test_validate_http_public_url():
    """公网 HTTP URL 通过验证。"""
    validate_url("http://example.com/post")


def test_validate_rejects_localhost():
    """localhost 被拒绝。"""
    with pytest.raises(ValidationError, match="localhost|internal|blocked"):
        validate_url("http://localhost/admin")


def test_validate_rejects_127_loopback():
    """127.0.0.1 被拒绝。"""
    with pytest.raises(ValidationError):
        validate_url("http://127.0.0.1/admin")


def test_validate_rejects_10_internal():
    """10.0.0.0/8 内网被拒绝。"""
    with pytest.raises(ValidationError):
        validate_url("http://10.0.0.1/internal")


def test_validate_rejects_192_168_internal():
    """192.168.0.0/16 内网被拒绝。"""
    with pytest.raises(ValidationError):
        validate_url("http://192.168.1.1/admin")


def test_validate_rejects_172_16_internal():
    """172.16.0.0/12 内网被拒绝。"""
    with pytest.raises(ValidationError):
        validate_url("http://172.16.0.1/admin")


def test_validate_rejects_cloud_metadata():
    """云元数据端点 169.254.169.254 被拒绝。"""
    with pytest.raises(ValidationError):
        validate_url("http://169.254.169.254/latest/meta-data/")


def test_validate_rejects_0_0_0_0():
    """0.0.0.0 被拒绝。"""
    with pytest.raises(ValidationError):
        validate_url("http://0.0.0.0/")


def test_validate_rejects_non_http_scheme():
    """非 http/https 协议被拒绝(file://、ftp://)。"""
    with pytest.raises(ValidationError, match="scheme|protocol"):
        validate_url("file:///etc/passwd")
    with pytest.raises(ValidationError):
        validate_url("ftp://example.com/file")


def test_validate_rejects_empty_url():
    """空 URL 被拒绝。"""
    with pytest.raises(ValidationError):
        validate_url("")


def test_validate_rejects_malformed_url():
    """格式错误的 URL 被拒绝。"""
    with pytest.raises(ValidationError):
        validate_url("not a url")
