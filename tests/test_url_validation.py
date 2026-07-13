from __future__ import annotations

import pytest

from app.exceptions import URLValidationError
from app.tools.safe_http import validate_public_url


def test_valid_http_url(resolver):
    result = validate_public_url("http://example.com/path#frag", resolver=resolver)
    assert result.normalized_url == "http://example.com/path"
    assert result.resolved_ips == ("93.184.216.34",)


def test_valid_https_url(resolver):
    result = validate_public_url("https://Example.com", resolver=resolver)
    assert result.normalized_url == "https://example.com/"


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/file",
        "https:///missing-host",
        "https://user:pass@example.com",
        "http://localhost",
        "http://127.0.0.1",
        "http://10.0.0.1",
        "http://172.16.0.1",
        "http://192.168.1.10",
        "http://169.254.169.254",
        "http://[::1]/",
        "http://[fc00::1]/",
        "http://[fe80::1]/",
        "http://metadata.google.internal/",
    ],
)
def test_blocked_urls(url, resolver):
    with pytest.raises(URLValidationError):
        validate_public_url(url, resolver=resolver)


def test_dns_resolving_to_blocked_ip_is_rejected():
    with pytest.raises(URLValidationError):
        validate_public_url("https://example.com", resolver=lambda host, port: ["10.0.0.5"])
