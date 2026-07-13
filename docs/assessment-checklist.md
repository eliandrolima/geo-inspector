# Checklist de Avaliação

Os documentos de requisitos lidos foram:

- `D:\SCTEC\Mini-Projeto-Avaliativo-2\Mini-Projeto-Avaliativo-Instrucoes-Para-GPT.md`
- `D:\SCTEC\Mini-Projeto-Avaliativo-2\Mini-Projeto-Avaliativo-Descricao.md`

## Critérios Acadêmicos

| Critério | Evidência no repositório |
| --- | --- |
| Branches e commits semânticos | Branches `main`, `develop` e `feature/initial-mvp`; commits locais semânticos. |
| Contribuição e produtividade | Histórico local de implementação, testes, documentação e organização. |
| Organização, documentação e prompts | `README.md`, `docs/prompts.md`, `docs/architecture.md`, `docs/examples.md`, `docs/assessment-checklist.md`. |
| Ideia do projeto e apresentação | `slides/geo-inspector.md` com exatamente dois slides. |
| LangGraph | `app/graph.py` usa `StateGraph`, nós, edges e rotas condicionais. |
| Ferramenta integrada | `fetch_webpage`, `inspect_site_files`, `extract_page_data` e `save_report`. |
| Segurança | `app/tools/safe_http.py`, `.env.example`, `.gitignore`, testes SSRF. |
| Contexto, memória e validação | `app/state.py`, `MemorySaver`, Pydantic schemas, reviewer e testes. |

## Requisitos Obrigatórios do MVP

| Requisito | Evidência |
| --- | --- |
| Receber uma URL | `POST /api/v1/audits`, `frontend/index.html`. |
| Validar e normalizar URL | `validate_public_url`. |
| Bloquear destinos inseguros | Testes em `tests/test_url_validation.py` e `tests/test_safe_http.py`. |
| Coletar HTML | `fetch_webpage`. |
| Consultar robots.txt e sitemap | `inspect_site_files`. |
| Extrair conteúdo principal | `extract_page_data`. |
| Auditoria técnica determinística | `run_technical_audit_node`. |
| Auditoria semântica com LLM | `run_semantic_audit_node`, `llm_factory.py`. |
| Reviewer com retry limitado | `review_findings_node`, testes de grafo. |
| Pontuação determinística | `calculate_geo_score`. |
| Relatórios JSON/Markdown | `report_writer.py`, `outputs/.gitkeep`. |
| Interface simples | `frontend/`. |
| Testes automatizados | `tests/`, 40 testes. |
| Documentação completa | `README.md` e `docs/`. |
| Slides | `slides/geo-inspector.md`. |

## Entregáveis

- Código-fonte do agente: `app/`.
- Ferramentas reais: `app/tools/`.
- Exemplos: `examples/sample-report.json` e `examples/sample-report.md`.
- Prompts: `docs/prompts.md` e `app/prompts/`.
- Apresentação: `slides/geo-inspector.md`.
- Testes: `tests/`.

## Limitações Registradas

- Sem crawler completo.
- Sem batch.
- Sem autenticação.
- Sem execução de JavaScript.
- Sem garantia de citação, indexação, recomendação ou posicionamento.
- Proteção SSRF apropriada ao MVP, mas não absoluta contra todas as formas de DNS rebinding.

## Divergência de Horário

Foi encontrada divergência no prazo de entrega de 20/07/2026:

- uma seção informa 20/07/2026 às 22h;
- o checklist final informa 20/07/2026 às 15h.

A divergência foi registrada sem escolher arbitrariamente um horário como correto.
