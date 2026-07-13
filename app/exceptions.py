class GEOInspectorError(Exception):
    """Base exception for expected GEO Inspector failures."""


class URLValidationError(GEOInspectorError):
    """Raised when a URL is malformed or blocked by safety policy."""


class DNSResolutionError(URLValidationError):
    """Raised when DNS resolution fails or returns no usable address."""


class FetchError(GEOInspectorError):
    """Raised when an HTTP fetch cannot complete safely."""


class FetchTimeoutError(FetchError):
    """Raised when a request times out."""


class ResponseTooLargeError(FetchError):
    """Raised when a response exceeds the configured byte limit."""


class UnsupportedContentTypeError(FetchError):
    """Raised when a response content type is not supported."""


class LLMConfigurationError(GEOInspectorError):
    """Raised when a real LLM provider is not configured."""


class LLMProviderError(GEOInspectorError):
    """Raised when the configured LLM provider cannot complete a request."""


class LLMSchemaError(GEOInspectorError):
    """Raised when an LLM response cannot be validated."""


class ReportStorageError(GEOInspectorError):
    """Raised when a report cannot be written or loaded safely."""
