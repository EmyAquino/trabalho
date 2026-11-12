import os
from contextlib import contextmanager
import psycopg2
from dotenv import load_dotenv

load_dotenv()

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS funcoes (
    id SERIAL PRIMARY KEY,
    descricao VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    funcao_id INTEGER NOT NULL REFERENCES funcoes(id),
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    senha VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS modalidades_formularios (
    id SERIAL PRIMARY KEY,
    descricao VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS autores (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    area VARCHAR(100) NOT NULL,
    cidade VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS instituicoes (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    cidade VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS formularios (
    id SERIAL PRIMARY KEY,
    autor_id INTEGER NOT NULL REFERENCES autores(id),
    modalidade_id INTEGER NOT NULL REFERENCES modalidades_formularios(id),
    instituicao_id INTEGER NOT NULL REFERENCES instituicoes(id),
    titulo VARCHAR(50) NOT NULL,
    resumo TEXT NOT NULL,
    arquivo BYTEA NOT NULL,
    palavra_chave VARCHAR(100) NOT NULL,
    area_conhecimento VARCHAR(255) NOT NULL
);
"""


@contextmanager
def get_connection():
    """Gerencia uma conexão PostgreSQL garantindo o fechamento ao sair do bloco with."""
    database_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    if database_url:
        conn = psycopg2.connect(database_url)
    else:
        conn = psycopg2.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            port=os.environ.get("DB_PORT", "5432"),
            dbname=os.environ.get("DB_NAME", "pense_submit"),
            user=os.environ.get("DB_USER", "postgres"),
            password=os.environ.get("DB_PASSWORD", "postgres"),
        )
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Garante a existência das tabelas e o seed básico de funções e modalidades."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)

            for descricao_funcao in ("Admin", "normal"):
                cur.execute(
                    "SELECT id FROM funcoes WHERE LOWER(descricao) = LOWER(%s) LIMIT 1;",
                    (descricao_funcao,),
                )
                if not cur.fetchone():
                    cur.execute(
                        "INSERT INTO funcoes (descricao) VALUES (%s);",
                        (descricao_funcao,),
                    )

            for descricao_mod in ("Ensino", "Pesquisa", "Extensão"):
                cur.execute(
                    "SELECT id FROM modalidades_formularios WHERE LOWER(descricao) = LOWER(%s) LIMIT 1;",
                    (descricao_mod,),
                )
                if not cur.fetchone():
                    cur.execute(
                        "INSERT INTO modalidades_formularios (descricao) VALUES (%s);",
                        (descricao_mod,),
                    )
        conn.commit()
