from __future__ import annotations

import logging

from app.logging_config import RedactSensitiveValuesFilter


def test_redacts_api_key_from_logged_urls():
    record = logging.LogRecord(
        name="httpx",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="HTTP Request: POST %s",
        args=("https://example.test/path?key=secret-value&other=1",),
        exc_info=None,
    )

    RedactSensitiveValuesFilter().filter(record)

    message = record.getMessage()
    assert "secret-value" not in message
    assert "key=[REDACTED]" in message
