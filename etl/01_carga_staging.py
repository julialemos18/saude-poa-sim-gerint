from pathlib import Path

import pandas as pd
from sqlalchemy import text

from db import get_engine

# Descobre a pasta raiz do projeto, onde quer que o script seja rodado
RAIZ = Path(__file__).resolve().parent.parent
ARQUIVOS = {
    "stg_gerint": RAIZ / "data" / "BD_gerint_solicitacoes.csv",
    "stg_sim": RAIZ / "data" / "BD_sim_obitos.csv",
}

engine = get_engine()

# Cria o "esquema" staging (uma gaveta separada dentro do banco)
with engine.begin() as conn:
    conn.execute(text("CREATE SCHEMA IF NOT EXISTS staging"))

for tabela, caminho in ARQUIVOS.items():
    # sep=";"    -> os CSVs usam ponto e vírgula
    # dtype=str  -> tudo entra como texto, sem o pandas "adivinhar" nada
    # na_values  -> célula vazia vira NULL
    df = pd.read_csv(caminho, sep=";", dtype=str,
                     keep_default_na=False, na_values=[""])
    print(f"{tabela}: {len(df)} linhas lidas do CSV")
    df.to_sql(tabela, engine, schema="staging", if_exists="replace",
              index=False, chunksize=2000, method="multi")

# Conferência: conta as linhas que realmente chegaram ao banco
with engine.connect() as conn:
    for tabela in ARQUIVOS:
        n = conn.execute(
            text(f"SELECT COUNT(*) FROM staging.{tabela}")).scalar()
        print(f"{tabela}: {n} linhas no banco")
