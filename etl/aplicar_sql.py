"""Executa um arquivo .sql no banco.
Uso (na raiz do projeto): python etl/aplicar_sql.py sql/01_esquema.sql
"""
import sys
from pathlib import Path

from sqlalchemy import text

from db import get_engine

RAIZ = Path(__file__).resolve().parent.parent

if len(sys.argv) != 2:
    print("Uso: python etl/aplicar_sql.py caminho/do/arquivo.sql")
    sys.exit(1)

caminho = RAIZ / sys.argv[1]
sql = caminho.read_text(encoding="utf-8")

engine = get_engine()
conexao = engine.raw_connection()
try:
    cursor = conexao.cursor()
    cursor.execute(sql)  # roda o arquivo inteiro numa transação só
    conexao.commit()
    print(f"OK: {sys.argv[1]} executado com sucesso.")
except Exception:
    conexao.rollback()  # se algo falhar, nada fica pela metade
    raise
finally:
    conexao.close()

with engine.connect() as conn:
    tabelas = conn.execute(text(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' ORDER BY table_name"
    )).fetchall()
print("Tabelas no esquema public:")
for (nome,) in tabelas:
    print(" -", nome)
