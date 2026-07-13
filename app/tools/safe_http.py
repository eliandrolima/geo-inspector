from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx

from app.config import Settings, get_settings
from app.exceptions import (
    DNSResolutionError,
    FetchError,
    FetchTimeoutError,
    ResponseTooLargeError,
    UnsupportedContentTypeError,
    URLValidationError,
)

Resolver = Callable[[str, int], Iterable[str]]

ALLOWED_SCHEMES = {"http", "https"}
DEFAULT_PORTS = {"http": 80, "https": 443}
BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata",
    "metadata.google.internal",
}
BLOCKED_NETWORKS = tuple(
    ipaddress.ip_network(network)
    for network in (
        "127.0.0.0/8",
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "169.254.0.0/16",
        "169.254.169.254/32",
        "::1/128",
        "fc00::/7",
        "fe80::/10",
    )
)


@dataclass(frozen=True)
class ValidatedUrl:
    original_url: str
    normalized_url: str
    hostname: str
    port: int
    resolved_ips: tuple[str, ...]


@dataclass
class FetchResult:
    status_code: int
    final_url: str
    content_type: str
    redirects: list[str] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)
    text: str = ""


def validate_public_url(
    url: str,
    *,
    resolver: Resolver | None = None,
) -> ValidatedUrl:
    """Normalize and validate a public HTTP(S) URL before any network access."""

    if not isinstance(url, str) or not url.strip():
        raise URLValidationError("A URL é obrigatória.")

    raw_url = url.strip()
    try:
        parsed = urlsplit(raw_url)
        port = parsed.port
    except ValueError as exc:
        raise URLValidationError("A URL possui porta ou formato inválido.") from exc

    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise URLValidationError("Apenas URLs http e https são aceitas.")
    if not parsed.hostname:
        raise URLValidationError("A URL deve possuir um hostname.")
    if parsed.username or parsed.password:
        raise URLValidationError("URLs com credenciais embutidas são bloqueadas.")

    scheme = parsed.scheme.lower()
    host = parsed.hostname.lower().rstrip(".")
    _validate_hostname_policy(host)
    port = port or DEFAULT_PORTS[scheme]
    resolved_ips = tuple(_resolve_and_validate_host(host, port, resolver=resolver))

    normalized_netloc = _build_netloc(host, port, scheme)
    normalized_path = parsed.path or "/"
    normalized_url = urlunsplit(
        (scheme, normalized_netloc, normalized_path, parsed.query, "")
    )
    return ValidatedUrl(
        original_url=raw_url,
        normalized_url=normalized_url,
        hostname=host,
        port=port,
        resolved_ips=resolved_ips,
    )


async def fetch_webpage(
    url: str,
    *,
    settings: Settings | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
    resolver: Resolver | None = None,
) -> FetchResult:
    return await fetch_text_resource(
        url,
        allowed_content_types=("text/html", "application/xhtml+xml"),
        settings=settings,
        transport=transport,
        resolver=resolver,
    )


async def fetch_text_resource(
    url: str,
    *,
    allowed_content_types: tuple[str, ...],
    settings: Settings | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
    resolver: Resolver | None = None,
) -> FetchResult:
    """Fetch a text resource with manual redirect validation and byte limits."""

    settings = settings or get_settings()
    current = validate_public_url(url, resolver=resolver).normalized_url
    redirects: list[str] = []
    timeout = httpx.Timeout(settings.request_timeout_seconds)

    async with httpx.AsyncClient(
        follow_redirects=False,
        timeout=timeout,
        transport=transport,
        headers={"User-Agent": settings.user_agent, "Accept": "*/*"},
    ) as client:
        for _ in range(settings.max_redirects + 1):
            try:
                async with client.stream("GET", current) as response:
                    if _is_redirect(response.status_code):
                        location = response.headers.get("location")
                        if not location:
                            raise FetchError("Redirecionamento sem cabeçalho Location.")
                        next_url = urljoin(current, location)
                        validated_next = validate_public_url(
                            next_url, resolver=resolver
                        )
                        redirects.append(validated_next.normalized_url)
                        current = validated_next.normalized_url
                        continue

                    if response.status_code >= 400:
                        raise FetchError(
                            f"A página respondeu com status HTTP {response.status_code}."
                        )

                    content_type = _content_type(response.headers)
                    if not _is_allowed_content_type(
                        content_type, allowed_content_types
                    ):
                        raise UnsupportedContentTypeError(
                            f"Tipo de conteúdo não suportado: {content_type or 'ausente'}."
                        )
                    body = await _read_limited_text(response, settings.max_response_bytes)
                    return FetchResult(
                        status_code=response.status_code,
                        final_url=current,
                        content_type=content_type,
                        redirects=redirects,
                        headers=_safe_headers(response.headers),
                        text=body,
                    )
            except httpx.TimeoutException as exc:
                raise FetchTimeoutError("Tempo limite excedido ao acessar a URL.") from exc
            except httpx.HTTPError as exc:
                raise FetchError("Falha HTTP ao acessar a URL.") from exc

        raise FetchError("Limite de redirecionamentos excedido.")

    raise FetchError("Falha inesperada ao finalizar a requisição.")


def _resolve_and_validate_host(
    host: str,
    port: int,
    *,
    resolver: Resolver | None,
) -> list[str]:
    try:
        ip_literal = ipaddress.ip_address(host)
    except ValueError:
        ip_literal = None

    if ip_literal is not None:
        _validate_public_ip(ip_literal)
        return [str(ip_literal)]

    try:
        addresses = list(resolver(host, port) if resolver else _socket_resolver(host, port))
    except socket.gaierror as exc:
        raise DNSResolutionError("Não foi possível resolver o hostname informado.") from exc

    if not addresses:
        raise DNSResolutionError("O hostname não retornou endereços IP.")

    validated: list[str] = []
    for address in addresses:
        ip_address = ipaddress.ip_address(address)
        _validate_public_ip(ip_address)
        validated.append(str(ip_address))
    return sorted(set(validated))


def _socket_resolver(host: str, port: int) -> list[str]:
    records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    addresses: list[str] = []
    for record in records:
        sockaddr = record[4]
        addresses.append(str(sockaddr[0]))
    return addresses


def _validate_hostname_policy(host: str) -> None:
    if host in BLOCKED_HOSTNAMES or host.endswith(".localhost"):
        raise URLValidationError("Hostname bloqueado pela política de segurança.")


def _validate_public_ip(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    for network in BLOCKED_NETWORKS:
        if address in network:
            raise URLValidationError("Destino bloqueado pela política anti-SSRF.")

    if (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
        or address.is_unspecified
        or not address.is_global
    ):
        raise URLValidationError("Endereço IP não público bloqueado.")


def _build_netloc(host: str, port: int, scheme: str) -> str:
    rendered_host = f"[{host}]" if ":" in host else host
    default_port = DEFAULT_PORTS[scheme]
    return rendered_host if port == default_port else f"{rendered_host}:{port}"


def _is_redirect(status_code: int) -> bool:
    return status_code in {301, 302, 303, 307, 308}


def _content_type(headers: httpx.Headers) -> str:
    return headers.get("content-type", "").split(";", 1)[0].strip().lower()


def _is_allowed_content_type(content_type: str, allowed: tuple[str, ...]) -> bool:
    return content_type in allowed


async def _read_limited_text(response: httpx.Response, max_bytes: int) -> str:
    chunks: list[bytes] = []
    size = 0
    async for chunk in response.aiter_bytes():
        size += len(chunk)
        if size > max_bytes:
            raise ResponseTooLargeError("A resposta excedeu o limite máximo de bytes.")
        chunks.append(chunk)
    return b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")


def _safe_headers(headers: httpx.Headers) -> dict[str, str]:
    allowed = {"content-type", "content-length", "last-modified", "etag"}
    return {key: value for key, value in headers.items() if key.lower() in allowed}
