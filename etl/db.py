import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

# Lê o arquivo .env (usuário, senha, etc.)
load_dotenv()


def get_engine():
    # Monta o "endereço" do banco: usuario:senha@maquina:porta/nome
    url = (
        f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )
    return create_engine(url)
