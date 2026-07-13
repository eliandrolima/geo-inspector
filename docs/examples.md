# Exemplos

## Entrada

```json
{
  "url": "https://example.com/article"
}
```

## Saída

Os arquivos `examples/sample-report.json` e `examples/sample-report.md` representam o mesmo relatório demonstrativo.

O exemplo é baseado na fixture local `tests/fixtures/article_complete.html`. Ele não corresponde a uma auditoria real executada na internet e não deve ser interpretado como validação externa de uma página pública.

## Interpretação do Relatório

- `execution_id`: identificador interno gerado pela aplicação.
- `status`: `completed` ou `error`.
- `geo_score`: pontuação heurística de 0 a 100.
- `classification`: faixa de prontidão calculada pelo código.
- `findings`: achados com categoria, critério, evidência, impacto, recomendação, prioridade e confiança.
- `score_breakdown`: pontos por categoria.
- `limitations`: limitações declaradas da auditoria.
- `disclaimer`: aviso de que a pontuação não garante citação, indexação ou posicionamento.

## Uso Manual

Com o servidor em execução:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/audits" `
  -ContentType "application/json" `
  -Body '{"url":"https://exemplo.com/artigo"}'
```

Para baixar:

```text
GET /api/v1/reports/{execution_id}/download?format=json
GET /api/v1/reports/{execution_id}/download?format=markdown
```
