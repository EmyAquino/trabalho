from database import get_connection


class Usuario:
    @staticmethod
    def autenticar(email: str, senha: str) -> dict | None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT u.id, u.nome, u.email, u.funcao_id, f.descricao
                    FROM usuarios u
                    JOIN funcoes f ON f.id = u.funcao_id
                    WHERE LOWER(u.email) = LOWER(%s) AND u.senha = %s
                    LIMIT 1;
                    """,
                    ((email or "").strip(), senha),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "id": row[0],
                    "nome": row[1],
                    "email": row[2],
                    "funcao_id": row[3],
                    "funcao": row[4],
                }

    @staticmethod
    def criar(nome: str, email: str, senha: str) -> int:
        nome = (nome or "").strip()
        email = (email or "").strip()
        if not nome or not email or not senha:
            raise ValueError("Preencha nome, e-mail e senha.")
        if len(nome) > 100 or len(email) > 100:
            raise ValueError("Nome e e-mail devem ter no máximo 100 caracteres.")
        if len(senha) > 20:
            raise ValueError("A senha deve ter no máximo 20 caracteres.")

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM usuarios WHERE LOWER(email) = LOWER(%s) LIMIT 1;",
                    (email,),
                )
                if cur.fetchone():
                    raise ValueError("E-mail já cadastrado.")

                cur.execute(
                    "SELECT id FROM funcoes WHERE LOWER(descricao) = 'normal' LIMIT 1;"
                )
                funcao_row = cur.fetchone()
                if not funcao_row:
                    cur.execute(
                        "INSERT INTO funcoes (descricao) VALUES ('normal') RETURNING id;"
                    )
                    funcao_id = cur.fetchone()[0]
                else:
                    funcao_id = funcao_row[0]

                cur.execute(
                    """
                    INSERT INTO usuarios (funcao_id, nome, email, senha)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (funcao_id, nome, email, senha),
                )
                novo_id = cur.fetchone()[0]
            conn.commit()
            return novo_id

    @staticmethod
    def listar_todos() -> list[dict]:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT u.id, u.nome, u.email, u.funcao_id, f.descricao
                    FROM usuarios u
                    JOIN funcoes f ON f.id = u.funcao_id
                    ORDER BY u.id ASC;
                    """
                )
                return [
                    {
                        "id": r[0],
                        "nome": r[1],
                        "email": r[2],
                        "funcao_id": r[3],
                        "funcao": r[4],
                    }
                    for r in cur.fetchall()
                ]

    @staticmethod
    def atualizar_funcao(usuario_id: int, nova_funcao_descricao: str) -> bool:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM funcoes WHERE LOWER(descricao) = LOWER(%s) LIMIT 1;",
                    (nova_funcao_descricao,),
                )
                funcao_row = cur.fetchone()
                if not funcao_row:
                    raise ValueError("Função inválida.")

                cur.execute(
                    "UPDATE usuarios SET funcao_id = %s WHERE id = %s;",
                    (funcao_row[0], usuario_id),
                )
                atualizado = cur.rowcount > 0
            conn.commit()
            return atualizado
