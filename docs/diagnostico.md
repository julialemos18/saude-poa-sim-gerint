# Diagnóstico de qualidade

## GERINT (14458 linhas)

| coluna | % nulo | distintos | 3 valores mais comuns |
|---|---|---|---|
| data_extracao | 0.0 | 1 | 2025-07-01 (14458) |
| identificador_pessoa2 | 0.0 | 14005 | 5700c3a74d3bfa9d62f8696c41a4a9 (454); c820fb59b1d27e14197ec530a4637a (1); 414a94711456d96ce875e07fe1b461 (1) |
| situacao | 0.0 | 1 | INTERNADA (14458) |
| central_regulacao_origem | 0.0 | 6 | CENTRAL DE REGULACAO HOSPITALA (8747); REGULACAO HOSPITALAR (4158); CENTRAL DE REGULACAO DE LEITOS (574) |
| data_solicitacao | 0.0 | 641 | 2025-06-27 (919); 2025-06-26 (882); 2025-06-25 (806) |
| sexo | 2.1 | 4 | MASCULINO (7350); FEMININO (6793); M (4) |
| idade | 2.1 | 104 | 0.0 (930); 72.0 (282); 70.0 (276) |
| municipio_residencia | 3.1 | 561 | PORTO ALEGRE (2613); CAXIAS DO SUL (451); CANOAS (403) |
| solicitante | 0.0 | 604 | HOSPITAL DE CLINICAS (876); HOSPITAL NOSSA SENHORA DA CONC (811); IRMANDADE DA SANTA CASA DE MIS (402) |
| municipio_solicitante | 0.0 | 327 | PORTO ALEGRE (4167); CAXIAS DO SUL (574); SANTA MARIA (511) |
| codigo_cid | 0.0 | 2296 | I64 (438); J180 (401); J189 (298) |
| carater | 0.0 | 3 | URGENCIA (12464); ELETIVA (1162); TRANSFERENCIA (832) |
| tipo_internacao | 0.0 | 2 | PRÓPRIA (10411); NÃO PRÓPRIA (4047) |
| tipo_leito | 0.0 | 8 | ENFADULTO (8619); PSIQUIATRICO (1853); UTIADULTO (1583) |
| data_autorizacao | 0.0 | 638 | 2025-06-27 (1022); 2025-06-26 (937); 2025-06-25 (867) |
| data_internacao | 0.0 | 54 | 2025-01-06 (11174); 2025-01-05 (1434); 2025-01-04 (453) |
| data_alta | 100.0 | 0 |  |
| executante | 0.0 | 244 | HOSPITAL DE CLINICAS (938); HOSPITAL NOSSA SENHORA DA CONC (892); ASSOCIACAO HOSPITALAR VILA NOV (565) |
| horas_na_fila | 0.0 | 2723 | 4143 (95); 4139 (76); 4144 (70) |

## SIM (135548 linhas)

| coluna | % nulo | distintos | 3 valores mais comuns |
|---|---|---|---|
| data_extracao | 0.0 | 1 | 2026-07-01 (135548) |
| identificador_pessoa2 | 60.2 | 710 | 68a4cfa2b1f6db5e762dd8287425fb (53249); ba26bf98238c16838daa644b6d3f54 (2); 244032504db535f7ea708183b7c97a (2) |
| obito | 0.0 | 132 | 03/2021 (2439); 04/2021 (1549); 08/2020 (1373) |
| nascimento | 1.5 | 1388 | 05/1935 (328); 10/1930 (324); 09/1930 (314) |
| escolaridade | 7.0 | 6 | IGNORADO (38520); DE 4 A 7 ANOS (26242); DE 1 A 3 ANOS (21173) |
| sexo | 0.1 | 2 | MASCULINO (68008); FEMININO (67432) |
| raca | 5.0 | 5 | BRANCA (106285); PRETA (13871); PARDA (8282) |
| gestacao | 97.4 | 6 | DE 37 A 41 SEM (916); DE 22 A 27 SEM (903); DE 32 A 36 SEM (703) |
| gravidez | 97.4 | 3 | ÚNICA (3184); DUPLA (303); TRIPLA OU MAIS (9) |
| tipo_obito | 0.0 | 2 | NÃO FETAL (133787); FETAL (1761) |
| circunstancia_obito | 91.4 | 5 | HOMICÍDIO (5790); ACIDENTE (4163); SUICÍDIO (1138) |
| cid_causa_basica | 0.0 | 2582 | I219 (6561); B342 (5781); C349 (4954) |
| obito_prematuro | 0.0 | 2 | NÃO (106912); SIM (28636) |
| obito_mulher_idade_fertil | 0.0 | 2 | NÃO (130162); SIM (5386) |

## Identificadores

**GERINT**: 0 nulos; 14005 distintos; mais repetidos:

identificador_pessoa2
5700c3a74d3bfa9d62f8696c41a4a983    454
c820fb59b1d27e14197ec530a4637ae7      1
414a94711456d96ce875e07fe1b4614a      1

**SIM**: 81587 nulos; 710 distintos; mais repetidos:

identificador_pessoa2
68a4cfa2b1f6db5e762dd8287425fb52    53249
ba26bf98238c16838daa644b6d3f5434        2
244032504db535f7ea708183b7c97a9f        2


IDs em comum entre GERINT e SIM: **0**

## Datas

- GERINT `data_solicitacao`: 2018-05-18 a 2025-06-30; valor mais frequente: 2025-06-27 (919 linhas)
- GERINT `data_autorizacao`: 2018-05-31 a 2025-06-30; valor mais frequente: 2025-06-27 (1022 linhas)
- GERINT `data_internacao`: 1982-01-01 a 2025-01-06; valor mais frequente: 2025-01-06 (11174 linhas)
- SIM `obito`: 2011-01-01 a 2021-12-01

## Fila (horas_na_fila)

- negativos: 123; min -58189; max 347842
- internação anterior à solicitação: 14334 linhas
- dias entre solicitação e autorização: mediana 0, P90 3, P99 28; 78.2% no mesmo dia