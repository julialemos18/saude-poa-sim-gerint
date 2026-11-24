# Sistema de Análise, Rastreamento e Gestão de Dados e de Indicadores em Saúde usando SIM e GERINT

Projeto final da disciplina de Bancos de Dados (Instituto de Informática, UFRGS).

**Autoras:** Brenda M. Soares, Julia F. Lemos e Lauren S. Lazaro

Este projeto modela, integra e analisa duas bases públicas do SUS em Porto Alegre:

- **GERINT** (Gerenciamento de Internações): solicitações de internação hospitalar e regulação de leitos (14.458 registros).
- **SIM** (Sistema de Informações sobre Mortalidade): declarações de óbito (135.548 registros).

O objetivo é construir um banco relacional integrado em PostgreSQL, um pipeline de tratamento em Python e um painel interativo em Streamlit, para consultar indicadores de cada base e compará-las de forma descritiva, sem presumir relação causal entre internações e óbitos.

> **Aviso importante:** as duas bases **não compartilham identificadores confiáveis** (nenhum ID em comum e muitos IDs ausentes ou repetidos no SIM). Os vínculos entre internações e óbitos serão **sintéticos** (gerados por regras explícitas) e todos os resultados que dependem deles são **experimentais**. Este trabalho demonstra o funcionamento do sistema e não produz conclusões epidemiológicas sobre a população de Porto Alegre.

---

## Tecnologias

| Função | Ferramenta |
|---|---|
| Banco de dados | PostgreSQL 16 (via Docker) |
| Tratamento de dados (ETL) | Python 3.11 ou superior, pandas, SQLAlchemy, psycopg2 |
| Interface | Streamlit e Plotly |

---

## Estrutura do repositório

```
.
├── app/                    # Painel Streamlit (em desenvolvimento)
├── data/                   # CSVs originais (GERINT e SIM)
├── docs/
│   └── diagnostico.md      # Relatório de qualidade dos dados (gerado pelo ETL)
├── etl/
│   ├── db.py               # Conexão com o banco
│   ├── 01_carga_staging.py # Carga bruta dos CSVs no esquema staging
│   ├── 02_diagnostico.py   # Diagnóstico de qualidade (gera docs/diagnostico.md)
│   └── aplicar_sql.py      # Executa um arquivo .sql no banco
├── sql/
│   └── 01_esquema.sql      # Esquema final (tabelas, chaves e restrições)
├── .env.example            # Modelo das configurações de conexão
├── docker-compose.yml      # Banco PostgreSQL
└── requirements.txt        # Dependências Python
```

---

## Como executar

Os comandos abaixo foram pensados para o **terminal bash do VS Code no Windows**. No Mac ou Linux, troque `source .venv/Scripts/activate` por `source .venv/bin/activate`.

### Pré-requisitos

- [Git](https://git-scm.com/downloads)
- [Python 3.11+](https://www.python.org/downloads/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop) (precisa estar **aberto** com o status "Engine running")
- [VS Code](https://code.visualstudio.com/)

### Passo a passo

```bash
# 1. Baixar o projeto
git clone https://github.com/USUARIO/saude-poa-sim-gerint.git
cd saude-poa-sim-gerint

# 2. Criar o arquivo de configuração (cópia do modelo)
cp .env.example .env

# 3. Criar e ativar o ambiente virtual Python
python -m venv .venv
source .venv/Scripts/activate

# 4. Instalar as bibliotecas
pip install -r requirements.txt

# 5. Ligar o banco de dados
docker compose up -d

# 6. Carga bruta dos CSVs (staging)
python etl/01_carga_staging.py

# 7. Diagnóstico de qualidade (gera docs/diagnostico.md)
python etl/02_diagnostico.py

# 8. Criar o esquema final
python etl/aplicar_sql.py sql/01_esquema.sql
```

Na carga bruta, a saída esperada tem 14.458 linhas para o GERINT e 135.548 para o SIM.

### Problemas comuns

| Problema | Solução |
|---|---|
| `ModuleNotFoundError` | O ambiente virtual não está ativo. Rode `source .venv/Scripts/activate` (o `(.venv)` deve aparecer no prompt). |
| `Connection refused` ao conectar | O banco está desligado. Abra o Docker Desktop e rode `docker compose up -d`. |
| `docker-credential-desktop not found` | Rode `export PATH="$PATH:/c/Program Files/Docker/Docker/resources/bin"` e tente de novo. |
| `Invalid requirement` no `pip install` | O `requirements.txt` deve ter apenas nomes de bibliotecas (comentários só com `#`). |
| Erro em variável do `.env` | O `.env` deve conter apenas linhas `NOME=valor` (cópia do `.env.example`). |

Comandos úteis do banco:

```bash
docker ps                                   # ver se o banco está rodando
docker compose down                         # desligar (os dados são mantidos)
docker compose exec db psql -U saude -d saude_poa   # abrir o console SQL
```

---

## Pipeline de dados

```
CSV originais → staging (dado cru) → diagnóstico → transformação → esquema final → consultas → painel
```

1. **Staging:** os CSVs são carregados sem alterações em `staging.stg_gerint` e `staging.stg_sim`, preservando o dado original.
2. **Diagnóstico:** perfil de cada coluna (nulos, valores distintos, domínios, datas, identificadores). Resultado em [`docs/diagnostico.md`](docs/diagnostico.md).
3. **Transformação:** padronização de categorias, datas, idades e CIDs, e tratamento de identificadores suspeitos.
4. **Esquema final:** tabelas relacionais com chaves primárias e estrangeiras, tabelas de domínio e restrições `CHECK`.
5. **Consultas e painel:** consultas SQL básicas e avançadas, expostas em um painel Streamlit.

---

## Modelo de dados

| Tabela | Descrição |
|---|---|
| `paciente` | Referência para solicitações e óbitos. Guarda o ID cifrado original (`id_origem`) e se ele é confiável (`id_confiavel`). |
| `solicitacao_internacao` | Solicitações do GERINT, com datas, perfil do paciente, CID, caráter, tipo de leito e fila. |
| `obito` | Óbitos do SIM, com datas, perfil sociodemográfico, causa básica e indicadores. No máximo um óbito por paciente. |
| `vinculo_sintetico` | Associações artificiais entre pacientes do GERINT e óbitos do SIM (**experimental**). |
| `dom_*` | Tabelas de domínio (sexo, caráter, tipo de leito, raça/cor, escolaridade, circunstância do óbito). |

O código CID de admissão (`codigo_cid`, GERINT) e a causa básica do óbito (`cid_causa_basica`, SIM) são mantidos em colunas **separadas**. Eles não são equivalentes e não são tratados como tal.

---

## Decisões de tratamento dos dados

Baseadas no diagnóstico de qualidade:

- **Identificadores:** 60% dos IDs do SIM são nulos e um único ID aparece em 53.249 linhas. No GERINT, um ID aparece em 454 linhas. IDs nulos ou suspeitos recebem `id_confiavel = false` e um paciente próprio por registro. Os IDs originais nunca são sobrescritos.
- **Fila (`horas_na_fila`):** o campo é inconsistente (valores negativos e internação anterior à solicitação). O tempo de espera é **recalculado** como `data_autorizacao − data_solicitacao`, em dias, e o valor original é guardado em `horas_na_fila_original`. Como só há data (sem hora) e cerca de 78% dos casos têm 0 dias, o corte para "fila alta" será definido por percentil (ex.: P90) e documentado.
- **Datas do SIM:** `MM/AAAA` vira `DATE` no dia 01. A idade no óbito é calculada a partir das datas.
- **Categorias:** `M` e `F` viram `MASCULINO` e `FEMININO`. Valores ausentes (nulos) e valores `IGNORADO` registrados na fonte permanecem distintos.
- **Períodos:** o SIM cobre 2011 a 2021, enquanto cerca de 94% das solicitações do GERINT são de 2025. Por isso o vínculo sintético usa uma `data_obito_sintetica`, e os resultados são rotulados como experimentais.

---

## Funcionalidades planejadas

**Básicas**
- Tempo registrado em fila por tipo de leito
- Perfil sociodemográfico de mortalidade (raça/cor, escolaridade, faixa etária)
- Volume de solicitações por estabelecimento
- Distribuição das solicitações por caráter
- Relatório de indicadores de mortalidade (com filtro de período e exportação)

**Avançadas**
- Vinculação sintética e análise temporal entre solicitações e óbitos (funções de janela)
- Análise multidimensional do tempo em fila (mediana, quartis e agrupamentos multidimensionais)

---

## Fontes dos dados

- Portal de Dados Abertos de Porto Alegre: <https://dadosabertos.poa.br/>
- Ministério da Saúde, Sistema de Informação sobre Mortalidade (SIM): <https://dadosabertos.saude.gov.br/dataset/sim>
- Dicionários de dados do GERINT e do SIM, fornecidos pela Prefeitura Municipal de Porto Alegre.
