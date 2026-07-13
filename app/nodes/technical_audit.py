from __future__ import annotations

from app.schemas.findings import Finding, FindingCategory, FindingPriority, FindingStatus
from app.state import AuditState


def run_technical_audit_node(state: AuditState) -> AuditState:
    metadata = state.get("metadata", {})
    robots = state.get("robots_data", {})
    sitemap = state.get("sitemap_data", {})
    findings = [
        _status_http(state),
        _redirects(state),
        _content_type(state),
        _robots(robots),
        _sitemap(sitemap),
        _title(metadata),
        _description(metadata),
        _canonical(metadata),
        _noindex(metadata),
        _h1(metadata),
        _heading_hierarchy(metadata),
        _language(metadata),
        _author(metadata),
        _dates(metadata),
        _links(metadata),
        _images_alt(metadata),
        _json_ld(metadata),
        _structured_data_citable(metadata),
        _content_length(metadata),
        _semantic_tags(metadata),
    ]
    return {
        "status": "technical_audit_completed",
        "technical_findings": [finding.model_dump(mode="json") for finding in findings],
    }


def _finding(
    *,
    category: FindingCategory,
    criterion: str,
    status: FindingStatus,
    source: str,
    observed: str,
    impact: str,
    recommendation: str,
    priority: FindingPriority,
    confidence: float,
) -> Finding:
    return Finding(
        category=category,
        criterion=criterion,
        status=status,
        evidence={"source": source, "observed": observed},
        impact=impact,
        recommendation=recommendation,
        priority=priority,
        confidence=confidence,
    )


def _status_http(state: AuditState) -> Finding:
    code = state.get("status_code")
    status = FindingStatus.PASSED if code and 200 <= code < 300 else FindingStatus.FAILED
    return _finding(
        category=FindingCategory.CRAWLABILITY,
        criterion="Status HTTP acessível",
        status=status,
        source="HTTP",
        observed=f"Status final observado: {code}.",
        impact="Status de sucesso permite que o conteúdo seja coletado para a auditoria.",
        recommendation="Manter a página acessível por HTTP/HTTPS público com resposta 2xx.",
        priority=FindingPriority.CRITICAL if status == FindingStatus.FAILED else FindingPriority.LOW,
        confidence=0.99,
    )


def _redirects(state: AuditState) -> Finding:
    redirects = state.get("redirects", [])
    status = FindingStatus.PASSED if len(redirects) <= 2 else FindingStatus.WARNING
    return _finding(
        category=FindingCategory.CRAWLABILITY,
        criterion="Redirecionamentos controlados",
        status=status,
        source="HTTP",
        observed=f"{len(redirects)} redirecionamento(s) observado(s).",
        impact="Cadeias longas de redirecionamento podem dificultar coleta e rastreio.",
        recommendation="Reduzir redirecionamentos e manter destinos finais públicos e estáveis.",
        priority=FindingPriority.MEDIUM if status == FindingStatus.WARNING else FindingPriority.LOW,
        confidence=0.95,
    )


def _content_type(state: AuditState) -> Finding:
    content_type = state.get("content_type", "")
    ok = content_type in {"text/html", "application/xhtml+xml"}
    return _finding(
        category=FindingCategory.CRAWLABILITY,
        criterion="Tipo de conteúdo HTML",
        status=FindingStatus.PASSED if ok else FindingStatus.FAILED,
        source="HTTP headers",
        observed=f"Content-Type final: {content_type or 'ausente'}.",
        impact="A auditoria do MVP depende de HTML estático para extrair conteúdo.",
        recommendation="Servir a página como text/html ou application/xhtml+xml.",
        priority=FindingPriority.HIGH if not ok else FindingPriority.LOW,
        confidence=0.98,
    )


def _robots(robots: dict) -> Finding:
    allowed = robots.get("allowed")
    if allowed is True:
        status = FindingStatus.PASSED
        observed = "robots.txt encontrado e permite o User-Agent do projeto."
    elif allowed is False:
        status = FindingStatus.FAILED
        observed = "robots.txt encontrado e não permite o User-Agent do projeto."
    else:
        status = FindingStatus.WARNING
        observed = f"robots.txt não verificado: {robots.get('error') or 'ausente'}."
    return _finding(
        category=FindingCategory.CRAWLABILITY,
        criterion="Robots.txt permite acesso",
        status=status,
        source="robots.txt",
        observed=observed,
        impact="Regras de robots podem afetar rastreabilidade por agentes autorizados.",
        recommendation="Publicar robots.txt claro e permitir acesso às páginas que devem ser auditáveis.",
        priority=FindingPriority.HIGH if status == FindingStatus.FAILED else FindingPriority.MEDIUM,
        confidence=0.9,
    )


def _sitemap(sitemap: dict) -> Finding:
    found = bool(sitemap.get("found"))
    return _finding(
        category=FindingCategory.CRAWLABILITY,
        criterion="Sitemap localizado",
        status=FindingStatus.PASSED if found else FindingStatus.WARNING,
        source="robots.txt/sitemap.xml",
        observed="Sitemap localizado." if found else "Nenhum sitemap foi localizado no escopo do MVP.",
        impact="Sitemaps ajudam sistemas automatizados a descobrir URLs relevantes.",
        recommendation="Disponibilizar sitemap.xml ou declarar sitemaps no robots.txt.",
        priority=FindingPriority.MEDIUM,
        confidence=0.85,
    )


def _title(metadata: dict) -> Finding:
    title = metadata.get("title")
    length = len(title or "")
    if not title:
        status = FindingStatus.FAILED
    elif 10 <= length <= 70:
        status = FindingStatus.PASSED
    else:
        status = FindingStatus.WARNING
    return _finding(
        category=FindingCategory.TECHNICAL,
        criterion="Title descritivo",
        status=status,
        source="HTML title",
        observed=f"Title: {title or 'ausente'} ({length} caracteres).",
        impact="Um title claro ajuda a identificar rapidamente o assunto da página.",
        recommendation="Usar um title único, descritivo e proporcional ao assunto principal.",
        priority=FindingPriority.HIGH if status == FindingStatus.FAILED else FindingPriority.MEDIUM,
        confidence=0.95,
    )


def _description(metadata: dict) -> Finding:
    description = metadata.get("description")
    length = len(description or "")
    if not description:
        status = FindingStatus.FAILED
    elif 50 <= length <= 170:
        status = FindingStatus.PASSED
    else:
        status = FindingStatus.WARNING
    return _finding(
        category=FindingCategory.TECHNICAL,
        criterion="Meta description",
        status=status,
        source="HTML meta description",
        observed=f"Meta description: {description or 'ausente'} ({length} caracteres).",
        impact="Descrições ajudam a resumir o conteúdo para leitores e sistemas.",
        recommendation="Adicionar uma descrição objetiva com o tema e valor da página.",
        priority=FindingPriority.HIGH if status == FindingStatus.FAILED else FindingPriority.MEDIUM,
        confidence=0.95,
    )


def _canonical(metadata: dict) -> Finding:
    canonical = metadata.get("canonical")
    return _finding(
        category=FindingCategory.TECHNICAL,
        criterion="Canonical",
        status=FindingStatus.PASSED if canonical else FindingStatus.WARNING,
        source="HTML link rel=canonical",
        observed=f"Canonical: {canonical or 'ausente'}.",
        impact="Canonical reduz ambiguidade sobre a URL principal do conteúdo.",
        recommendation="Adicionar link rel=canonical apontando para a URL preferencial.",
        priority=FindingPriority.MEDIUM,
        confidence=0.9,
    )


def _noindex(metadata: dict) -> Finding:
    robots = str(metadata.get("meta_robots") or "").lower()
    blocked = "noindex" in robots
    return _finding(
        category=FindingCategory.TECHNICAL,
        criterion="Meta robots noindex",
        status=FindingStatus.FAILED if blocked else FindingStatus.PASSED,
        source="HTML meta robots",
        observed=f"Meta robots: {robots or 'ausente'}; noindex detectado: {blocked}.",
        impact="noindex sinaliza que a página não deve ser indexada por mecanismos compatíveis.",
        recommendation="Remover noindex quando a página deve ser publicamente encontrável.",
        priority=FindingPriority.CRITICAL if blocked else FindingPriority.LOW,
        confidence=0.98,
    )


def _h1(metadata: dict) -> Finding:
    count = int(metadata.get("h1_count") or 0)
    if count == 1:
        status = FindingStatus.PASSED
    elif count == 0:
        status = FindingStatus.FAILED
    else:
        status = FindingStatus.WARNING
    return _finding(
        category=FindingCategory.TECHNICAL,
        criterion="H1 único",
        status=status,
        source="HTML headings",
        observed=f"Quantidade de H1: {count}.",
        impact="Um H1 claro ajuda a identificar o tópico principal da página.",
        recommendation="Manter exatamente um H1 descritivo para o conteúdo principal.",
        priority=FindingPriority.HIGH if status == FindingStatus.FAILED else FindingPriority.MEDIUM,
        confidence=0.95,
    )


def _heading_hierarchy(metadata: dict) -> Finding:
    headings = metadata.get("headings", [])
    levels = [int(item.get("level", 0)) for item in headings]
    jumps = any(curr - prev > 1 for prev, curr in zip(levels, levels[1:]))
    status = FindingStatus.WARNING if jumps else FindingStatus.PASSED
    if not levels:
        status = FindingStatus.FAILED
    return _finding(
        category=FindingCategory.TECHNICAL,
        criterion="Hierarquia de headings",
        status=status,
        source="HTML headings",
        observed=f"Níveis encontrados: {levels or 'nenhum'}.",
        impact="Hierarquia consistente facilita leitura e segmentação do conteúdo.",
        recommendation="Organizar headings em ordem lógica, evitando saltos como H2 para H4.",
        priority=FindingPriority.MEDIUM,
        confidence=0.9,
    )


def _language(metadata: dict) -> Finding:
    language = metadata.get("language")
    return _finding(
        category=FindingCategory.TECHNICAL,
        criterion="Idioma declarado",
        status=FindingStatus.PASSED if language else FindingStatus.WARNING,
        source="HTML lang",
        observed=f"Idioma declarado: {language or 'ausente'}.",
        impact="O idioma declarado melhora interpretação por leitores e sistemas.",
        recommendation="Adicionar o atributo lang no elemento html.",
        priority=FindingPriority.LOW,
        confidence=0.9,
    )


def _author(metadata: dict) -> Finding:
    author = metadata.get("author")
    return _finding(
        category=FindingCategory.AUTHORITY,
        criterion="Autoria detectável",
        status=FindingStatus.PASSED if author else FindingStatus.FAILED,
        source="HTML/metadados",
        observed=f"Autor detectado: {author or 'nenhum autor identificado nos dados analisados'}.",
        impact="Autoria clara contribui para responsabilidade editorial percebida.",
        recommendation="Adicionar nome, qualificação e perfil do autor ou responsável editorial.",
        priority=FindingPriority.HIGH,
        confidence=0.9,
    )


def _dates(metadata: dict) -> Finding:
    published = metadata.get("published_time")
    modified = metadata.get("modified_time")
    ok = bool(published or modified)
    return _finding(
        category=FindingCategory.AUTHORITY,
        criterion="Datas editoriais",
        status=FindingStatus.PASSED if ok else FindingStatus.WARNING,
        source="HTML/metadados",
        observed=f"Publicação: {published or 'ausente'}; atualização: {modified or 'ausente'}.",
        impact="Datas ajudam a avaliar atualidade e manutenção do conteúdo.",
        recommendation="Informar data de publicação e, quando aplicável, data de atualização.",
        priority=FindingPriority.MEDIUM,
        confidence=0.88,
    )


def _links(metadata: dict) -> Finding:
    links = metadata.get("links", {})
    external_count = int(links.get("external_count") or 0)
    internal_count = int(links.get("internal_count") or 0)
    status = FindingStatus.PASSED if external_count > 0 else FindingStatus.WARNING
    return _finding(
        category=FindingCategory.EVIDENCE,
        criterion="Inventário de links",
        status=status,
        source="HTML links",
        observed=f"Links internos: {internal_count}; links externos: {external_count}.",
        impact="Referências externas verificáveis podem apoiar evidências e contexto.",
        recommendation="Adicionar links para fontes relevantes quando houver afirmações verificáveis.",
        priority=FindingPriority.MEDIUM,
        confidence=0.85,
    )


def _images_alt(metadata: dict) -> Finding:
    images = metadata.get("images", [])
    missing = metadata.get("images_without_alt", [])
    if not images:
        status = FindingStatus.NOT_APPLICABLE
    elif not missing:
        status = FindingStatus.PASSED
    elif len(missing) == len(images):
        status = FindingStatus.FAILED
    else:
        status = FindingStatus.WARNING
    return _finding(
        category=FindingCategory.TECHNICAL,
        criterion="Imagens com texto alternativo",
        status=status,
        source="HTML img",
        observed=f"Imagens: {len(images)}; sem alt: {len(missing)}.",
        impact="Textos alternativos melhoram acessibilidade e interpretação do conteúdo visual.",
        recommendation="Adicionar alt objetivo nas imagens informativas.",
        priority=FindingPriority.MEDIUM,
        confidence=0.9,
    )


def _json_ld(metadata: dict) -> Finding:
    count = int(metadata.get("json_ld_count") or 0)
    return _finding(
        category=FindingCategory.TECHNICAL,
        criterion="Dados estruturados JSON-LD",
        status=FindingStatus.PASSED if count else FindingStatus.WARNING,
        source="HTML script application/ld+json",
        observed=f"Blocos JSON-LD encontrados: {count}.",
        impact="Dados estruturados ajudam sistemas a interpretar entidades e contexto.",
        recommendation="Adicionar JSON-LD coerente com o tipo de página quando aplicável.",
        priority=FindingPriority.MEDIUM,
        confidence=0.9,
    )


def _structured_data_citable(metadata: dict) -> Finding:
    schema_types = metadata.get("schema_types", [])
    return _finding(
        category=FindingCategory.EVIDENCE,
        criterion="Tipos Schema.org detectados",
        status=FindingStatus.PASSED if schema_types else FindingStatus.WARNING,
        source="JSON-LD",
        observed=f"Tipos Schema.org detectados: {schema_types or 'nenhum'}.",
        impact="Tipos estruturados podem reforçar o contexto da entidade ou artigo.",
        recommendation="Usar tipos Schema.org compatíveis, como Article, Product ou Organization.",
        priority=FindingPriority.LOW,
        confidence=0.85,
    )


def _content_length(metadata: dict) -> Finding:
    word_count = int(metadata.get("word_count") or 0)
    if word_count >= 800:
        status = FindingStatus.PASSED
    elif word_count >= 300:
        status = FindingStatus.WARNING
    else:
        status = FindingStatus.FAILED
    return _finding(
        category=FindingCategory.CLARITY,
        criterion="Tamanho do conteúdo textual",
        status=status,
        source="Texto extraído",
        observed=f"Total aproximado de palavras: {word_count}.",
        impact="Conteúdo muito curto pode limitar a análise semântica e a utilidade da resposta.",
        recommendation="Expandir o conteúdo com explicações, respostas diretas e evidências.",
        priority=FindingPriority.HIGH if status == FindingStatus.FAILED else FindingPriority.MEDIUM,
        confidence=0.88,
    )


def _semantic_tags(metadata: dict) -> Finding:
    tags = metadata.get("semantic_tags", {})
    has_main = bool(tags.get("article") or tags.get("main"))
    return _finding(
        category=FindingCategory.TECHNICAL,
        criterion="Elementos semânticos",
        status=FindingStatus.PASSED if has_main else FindingStatus.WARNING,
        source="HTML semântico",
        observed=f"Contagem de tags semânticas: {tags}.",
        impact="Elementos como article e main indicam o bloco principal do conteúdo.",
        recommendation="Usar article ou main para delimitar o conteúdo central da página.",
        priority=FindingPriority.MEDIUM,
        confidence=0.88,
    )
