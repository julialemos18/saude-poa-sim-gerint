"""Funções compartilhadas do painel: conexão e execução das consultas.

As consultas ficam em sql/02_consultas_basicas.sql (cada uma com um
'-- name: nome'). Aqui lemos esse arquivo e executamos pelo nome.
Os valores digitados pelo usuário vão como PARÂMETROS (:nome), nunca
concatenados no texto SQL (isso evita injeção SQL).
"""
import re
import sys
from decimal import Decimal
from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy import text

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "etl"))  # para reaproveitar etl/db.py
from db import get_engine  # noqa: E402  # type: ignore

ARQUIVO_SQL = RAIZ / "sql" / "02_consultas_basicas.sql"


@st.cache_resource
def engine():
    return get_engine()


@st.cache_data
def carregar_consultas():
    """Lê o arquivo .sql e devolve {nome: texto_sql}."""
    conteudo = ARQUIVO_SQL.read_text(encoding="utf-8")
    consultas = {}
    for bloco in re.split(r"^-- name:\s*", conteudo, flags=re.MULTILINE)[1:]:
        nome, _, corpo = bloco.partition("\n")
        # tira os comentários (um ":" dentro de comentário confundiria os parâmetros)
        linhas = [l for l in corpo.splitlines(
        ) if not l.strip().startswith("--")]
        consultas[nome.strip()] = "\n".join(linhas).strip().rstrip(";")
    return consultas


@st.cache_data(ttl=600, show_spinner=False)
def consultar(nome, **parametros):
    """Executa a consulta 'nome' e devolve um DataFrame."""
    sql = carregar_consultas()[nome]
    with engine().connect() as conn:
        df = pd.read_sql(text(sql), conn, params=parametros)
    for coluna in df.columns:  # o banco devolve numeric como Decimal
        if df[coluna].map(lambda v: isinstance(v, Decimal)).any():
            df[coluna] = df[coluna].astype(float)
    return df


def csv_para_download(df):
    """CSV com acentos corretos ao abrir no Excel."""
    return df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
