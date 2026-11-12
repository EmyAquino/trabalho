import os
from contextlib import contextmanager
import psycopg2
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

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
    cpf VARCHAR(14) NOT NULL DEFAULT '',
    instituicao VARCHAR(150) NOT NULL DEFAULT '',
    senha VARCHAR(255) NOT NULL
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
    area_conhecimento VARCHAR(255) NOT NULL,
    data_envio TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'Pendente'
);
"""

MIGRACOES_SQL = """
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS cpf VARCHAR(14) NOT NULL DEFAULT '';
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS instituicao VARCHAR(150) NOT NULL DEFAULT '';
ALTER TABLE usuarios ALTER COLUMN senha TYPE VARCHAR(255);
ALTER TABLE formularios ADD COLUMN IF NOT EXISTS data_envio TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE formularios ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'Pendente';
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
    """Garante a existência das tabelas, colunas novas e seed básico."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
            cur.execute(MIGRACOES_SQL)

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

            # Cria um avaliador padrão para facilitar os testes do painel
            cur.execute(
                """
                UPDATE usuarios
                SET cpf = '123.456.789-09'
                WHERE LOWER(email) = 'avaliador@ifrs.edu.br' AND cpf = '000.000.000-00';
                """
            )
            cur.execute(
                "SELECT id FROM usuarios WHERE LOWER(email) = LOWER(%s) LIMIT 1;",
                ("avaliador@ifrs.edu.br",),
            )
            if not cur.fetchone():
                cur.execute(
                    "SELECT id FROM funcoes WHERE LOWER(descricao) = 'admin' LIMIT 1;"
                )
                admin_row = cur.fetchone()
                if admin_row:
                    cur.execute(
                        """
                        INSERT INTO usuarios (funcao_id, nome, email, cpf, instituicao, senha)
                        VALUES (%s, %s, %s, %s, %s, %s);
                        """,
                        (
                            admin_row[0],
                            "Avaliador IFRS",
                            "avaliador@ifrs.edu.br",
                            "123.456.789-09",
                            "IFRS - Reitoria",
                            generate_password_hash("admin123"),
                        ),
                    )
        conn.commit()
