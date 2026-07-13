# Slide 1 — Problema e Solução

**Problema:** páginas pensadas só para SEO tradicional podem ser pouco claras, pouco estruturadas e difíceis de auditar para prontidão GEO.

**Público beneficiado:** proprietários de sites, desenvolvedores e produtores de conteúdo.

**Processo automatizado:** receber uma URL pública, coletar HTML, extrair metadados, auditar critérios técnicos e semânticos, revisar achados e gerar relatório.

**Proposta do agente:** GEO Inspector, um agente controlado por LangGraph com ferramentas reais, estado compartilhado, validação e relatório estruturado.

**Entrada:** uma URL pública.

**Saída:** pontuação heurística, classificação, evidências, recomendações, ações rápidas e downloads em JSON/Markdown.

---

# Slide 2 — Arquitetura e Tecnologias

**Fluxo LangGraph:** validação → fetch seguro → robots/sitemap → extração → planner → auditoria técnica → auditoria semântica → reviewer → pontuação → relatório.

**Estado e memória:** `AuditState` mantém contexto da execução; `MemorySaver` preserva estado e retry.

**Ferramentas:** HTTPX seguro, inspeção de site files, parser BeautifulSoup e escritor de relatórios.

**Reviewer:** valida schema, evidências, duplicações e retry único da auditoria semântica.

**Tecnologias:** Python, FastAPI, LangGraph, Pydantic, HTTPX, BeautifulSoup, pytest, HTML/CSS/JS puro.

**Segurança:** bloqueio SSRF, redirects revalidados, limite de bytes, timeout, `.env.example`, prompts contra prompt injection e sem execução de JavaScript.
