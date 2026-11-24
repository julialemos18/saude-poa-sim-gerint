-- =====================================================================
-- Consultas básicas (GERINT e SIM)
-- Cada consulta começa com "-- name: nome". O painel (app/) lê este
-- arquivo e executa cada uma pelo nome. Parâmetros aparecem como :nome
-- (para testar no psql, troque :nome por um valor).
-- =====================================================================


-- name: fila_por_leito
-- Pergunta (GERINT): quais tipos de leito têm maior tempo de espera?
-- Medida: dias entre solicitação e autorização (a coluna horas_na_fila
-- original é inconsistente; ver docs/diagnostico.md). Só há data, sem hora.
SELECT
    s.tipo_leito,
    l.descricao                                   AS leito,
    COUNT(*)                                      AS solicitacoes,
    ROUND(AVG(s.dias_ate_autorizacao), 2)         AS media_dias,
    CAST(percentile_cont(0.5) WITHIN GROUP (ORDER BY s.dias_ate_autorizacao) AS numeric) AS mediana_dias,
    CAST(percentile_cont(0.9) WITHIN GROUP (ORDER BY s.dias_ate_autorizacao) AS numeric) AS p90_dias,
    MAX(s.dias_ate_autorizacao)                   AS maximo_dias
FROM solicitacao_internacao s
JOIN dom_tipo_leito l ON l.valor = s.tipo_leito
WHERE NOT s.fila_inconsistente
GROUP BY s.tipo_leito, l.descricao
ORDER BY media_dias DESC;


-- name: perfil_raca
-- Pergunta (SIM): como os óbitos se distribuem por raça/cor?
SELECT
    COALESCE(raca, 'NÃO INFORMADO')               AS raca,
    COUNT(*)                                      AS obitos,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS percentual
FROM obito
GROUP BY COALESCE(raca, 'NÃO INFORMADO')
ORDER BY obitos DESC;


-- name: perfil_escolaridade
-- Pergunta (SIM): como os óbitos se distribuem por escolaridade?
-- IGNORADO (registrado na fonte) e NÃO INFORMADO (vazio) ficam separados.
SELECT
    COALESCE(o.escolaridade, 'NÃO INFORMADO')     AS escolaridade,
    COUNT(*)                                      AS obitos,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS percentual
FROM obito o
LEFT JOIN dom_escolaridade e ON e.valor = o.escolaridade
GROUP BY COALESCE(o.escolaridade, 'NÃO INFORMADO')
ORDER BY MIN(COALESCE(e.ordem, 99));


-- name: perfil_faixa_etaria
-- Pergunta (SIM): como os óbitos se distribuem por faixa etária?
-- Idade em anos completos na data do óbito (a fonte só tem mês/ano).
WITH base AS (
    SELECT
        CASE
            WHEN idade_obito IS NULL THEN 'NÃO INFORMADA'
            WHEN idade_obito < 5     THEN '0 a 4 anos'
            WHEN idade_obito < 20    THEN '5 a 19 anos'
            WHEN idade_obito < 40    THEN '20 a 39 anos'
            WHEN idade_obito < 60    THEN '40 a 59 anos'
            WHEN idade_obito < 80    THEN '60 a 79 anos'
            ELSE '80 anos ou mais'
        END AS faixa_etaria,
        CASE
            WHEN idade_obito IS NULL THEN 99
            WHEN idade_obito < 5     THEN 1
            WHEN idade_obito < 20    THEN 2
            WHEN idade_obito < 40    THEN 3
            WHEN idade_obito < 60    THEN 4
            WHEN idade_obito < 80    THEN 5
            ELSE 6
        END AS ordem
    FROM obito
)
SELECT
    faixa_etaria,
    COUNT(*)                                      AS obitos,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS percentual
FROM base
GROUP BY faixa_etaria, ordem
ORDER BY ordem;


-- name: solicitacoes_por_estabelecimento
-- Pergunta (GERINT): quais estabelecimentos solicitantes têm mais solicitações?
-- Parâmetro: :limite (quantos estabelecimentos mostrar)
SELECT
    solicitante,
    municipio_solicitante,
    COUNT(*)                                      AS solicitacoes,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS percentual
FROM solicitacao_internacao
GROUP BY solicitante, municipio_solicitante
ORDER BY solicitacoes DESC, solicitante
LIMIT :limite;


-- name: distribuicao_carater
-- Pergunta (GERINT): qual a distribuição das solicitações por caráter?
SELECT
    c.valor                                       AS carater,
    COUNT(s.id_solicitacao)                       AS solicitacoes,
    ROUND(100.0 * COUNT(s.id_solicitacao) / SUM(COUNT(s.id_solicitacao)) OVER (), 1) AS percentual
FROM dom_carater c
LEFT JOIN solicitacao_internacao s ON s.carater = c.valor
GROUP BY c.valor
ORDER BY solicitacoes DESC;


-- name: periodo_obitos
-- Menor e maior data de óbito (limites do filtro de período do painel).
SELECT MIN(data_obito) AS inicio, MAX(data_obito) AS fim
FROM obito;


-- name: mortalidade_resumo
-- Pergunta (SIM): quantos óbitos e de que tipo no período?
-- Parâmetros: :inicio e :fim (datas)
SELECT
    COUNT(*)                                          AS obitos,
    COUNT(*) FILTER (WHERE tipo_obito = 'FETAL')      AS fetais,
    COUNT(*) FILTER (WHERE obito_prematuro)           AS prematuros,
    COUNT(*) FILTER (WHERE obito_mulher_idade_fertil) AS mulheres_idade_fertil
FROM obito
WHERE data_obito BETWEEN :inicio AND :fim;


-- name: mortalidade_por_mes
-- Pergunta (SIM): como os óbitos evoluem mês a mês?
-- Parâmetros: :inicio e :fim (datas)
SELECT
    data_obito                                    AS mes,
    COUNT(*)                                      AS obitos
FROM obito
WHERE data_obito BETWEEN :inicio AND :fim
GROUP BY data_obito
ORDER BY data_obito;


-- name: mortalidade_por_causa
-- Pergunta (SIM): quais as principais causas básicas (categoria CID)?
-- Parâmetros: :inicio, :fim (datas) e :limite (quantas causas mostrar)
SELECT
    grupo_cid,
    COUNT(*)                                      AS obitos,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS percentual
FROM obito
WHERE data_obito BETWEEN :inicio AND :fim
  AND grupo_cid IS NOT NULL
GROUP BY grupo_cid
ORDER BY obitos DESC, grupo_cid
LIMIT :limite;