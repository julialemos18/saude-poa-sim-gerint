from pathlib import Path

import pandas as pd

from db import get_engine

RAIZ = Path(__file__).resolve().parent.parent
engine = get_engine()

# Lê as duas tabelas de staging para dentro do pandas
g = pd.read_sql("SELECT * FROM staging.stg_gerint", engine)
s = pd.read_sql("SELECT * FROM staging.stg_sim", engine)


def perfil(df, nome):
    """Monta uma tabela com o perfil de cada coluna."""
    linhas = [f"## {nome} ({len(df)} linhas)\n",
              "| coluna | % nulo | distintos | 3 valores mais comuns |",
              "|---|---|---|---|"]
    for c in df.columns:
        vc = df[c].value_counts()
        top = "; ".join(f"{str(k)[:30]} ({v})" for k, v in vc.head(3).items())
        linhas.append(f"| {c} | {df[c].isna().mean()*100:.1f} | "
                      f"{df[c].nunique()} | {top.replace('|', '/')} |")
    return "\n".join(linhas) + "\n"


saida = ["# Diagnóstico de qualidade\n", perfil(g, "GERINT"), perfil(s, "SIM")]

# --- Identificadores
saida.append("## Identificadores\n")
for nome, df in [("GERINT", g), ("SIM", s)]:
    ids = df["identificador_pessoa2"]
    saida.append(f"**{nome}**: {ids.isna().sum()} nulos; "
                 f"{ids.nunique()} distintos; mais repetidos:\n")
    saida.append(ids.value_counts().head(3).to_string() + "\n")
inter = set(g["identificador_pessoa2"].dropna()) & set(
    s["identificador_pessoa2"].dropna())
saida.append(f"\nIDs em comum entre GERINT e SIM: **{len(inter)}**\n")

# --- Datas
saida.append("## Datas\n")
for col in ["data_solicitacao", "data_autorizacao", "data_internacao"]:
    d = pd.to_datetime(g[col], errors="coerce")
    saida.append(f"- GERINT `{col}`: {d.min().date()} a {d.max().date()}; "
                 f"valor mais frequente: {g[col].mode()[0]} ({(g[col] == g[col].mode()[0]).sum()} linhas)")
d = pd.to_datetime(s["obito"], format="%m/%Y", errors="coerce")
saida.append(f"- SIM `obito`: {d.min().date()} a {d.max().date()}")

# --- Fila
h = pd.to_numeric(g["horas_na_fila"], errors="coerce")
sol = pd.to_datetime(g["data_solicitacao"], errors="coerce")
aut = pd.to_datetime(g["data_autorizacao"], errors="coerce")
inte = pd.to_datetime(g["data_internacao"], errors="coerce")
saida.append("\n## Fila (horas_na_fila)\n")
saida.append(
    f"- negativos: {(h < 0).sum()}; min {h.min():.0f}; max {h.max():.0f}")
saida.append(
    f"- internação anterior à solicitação: {(inte < sol).sum()} linhas")
dias = (aut - sol).dt.days
saida.append(f"- dias entre solicitação e autorização: mediana {dias.median():.0f}, "
             f"P90 {dias.quantile(.9):.0f}, P99 {dias.quantile(.99):.0f}; "
             f"{(dias == 0).mean()*100:.1f}% no mesmo dia")

# Salva tudo num arquivo markdown
(RAIZ / "docs" / "diagnostico.md").write_text("\n".join(saida), encoding="utf-8")
print("Gerado: docs/diagnostico.md")
