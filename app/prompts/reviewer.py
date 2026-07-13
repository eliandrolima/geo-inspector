REVIEWER_RULES = """O reviewer valida os achados antes da pontuação.

Verificações:
- schema Pydantic válido;
- evidência presente e observável;
- recomendação ligada à evidência;
- categoria, status e prioridade permitidos;
- confiança entre 0 e 1;
- duplicações por categoria e critério;
- ausência de afirmações técnicas não sustentadas;
- quantidade mínima de achados semânticos aplicáveis.

Se falhar, o grafo permite no máximo uma nova tentativa da auditoria semântica.
"""
