import logging
import re

from app.config import Settings

SENSITIVE_QUERY_RE = re.compile(r"(?i)([?&](?:key|api_key|token|access_token)=)([^&\s]+)")
SENSITIVE_HEADER_RE = re.compile(r"(?i)(authorization:\s*bearer\s+)([^\s,]+)")


def configure_logging(settings: Settings) -> None:
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    redaction_filter = RedactSensitiveValuesFilter()
    for logger_name in ("", "httpx", "httpcore"):
        logger = logging.getLogger(logger_name)
        logger.addFilter(redaction_filter)


class RedactSensitiveValuesFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _redact_value(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(_redact_value(arg) for arg in record.args)
        elif isinstance(record.args, dict):
            record.args = {key: _redact_value(value) for key, value in record.args.items()}
        return True


def _redact_value(value):
    if not isinstance(value, str):
        rendered = str(value)
        if "key=" not in rendered.lower() and "token=" not in rendered.lower():
            return value
        value = rendered
    value = SENSITIVE_QUERY_RE.sub(r"\1[REDACTED]", value)
    return SENSITIVE_HEADER_RE.sub(r"\1[REDACTED]", value)
