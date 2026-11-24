# Relatório da transformação e carga

| Tabela | Linhas no staging | Carregadas | Rejeitadas |
|---|---|---|---|
| solicitacao_internacao (GERINT) | 14458 | 14458 | 0 |
| obito (SIM) | 135548 | 135548 | 0 |

**Pacientes criados:** 150006 no total
- GERINT: 14004 com ID confiável e 454 sem (ID nulo ou suspeito)
- SIM: 706 com ID confiável e 134842 sem (ID nulo ou suspeito)

**Fila recalculada** (data_autorizacao − data_solicitacao, em dias): 2 linhas marcadas como inconsistentes (sem data de autorização ou acima de 365 dias).
- Entre as demais: mediana 0, P90 3, P99 28; 78.2% no mesmo dia.
