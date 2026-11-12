from werkzeug.security import check_password_hash, generate_password_hash
from database.database import get_connection


def _validar_email(email: str) -> str:
    email = (email or "").strip()
    if not email:
        raise ValueError("Informe o e-mail.")
    if len(email) > 100:
        raise ValueError("O e-mail deve ter no máximo 100 caracteres.")
    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValueError("Informe um e-mail válido.")
    return email


def _formatar_cpf(cpf: str) -> str:
    apenas_numeros = "".join(c for c in (cpf or "") if c.isdigit())
    if len(apenas_numeros) != 11 or len(set(apenas_numeros)) == 1:
        raise ValueError("Informe um CPF válido com 11 números.")
    return (
        f"{apenas_numeros[:3]}.{apenas_numeros[3:6]}."
        f"{apenas_numeros[6:9]}-{apenas_numeros[9:]}"
    )


def _verificar_senha(senha_salva: str, senha_digitada: str) -> bool:
    if not senha_salva or not senha_digitada:
        return False
    # Suporta hash do Werkzeug e também senhas antigas salvas em texto puro
    if senha_salva.startswith(("scrypt:", "pbkdf2:")):
        return check_password_hash(senha_salva, senha_digitada)
    return senha_salva == senha_digitada


class Usuario:
    @staticmethod
    def autenticar(email: str, senha: str):
        email_limpo = (email or "").strip()
        if not email_limpo or not senha:
            return None

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT u.id, u.nome, u.email, u.cpf, u.instituicao,
                           u.senha, u.funcao_id, f.descricao
                    FROM usuarios u
                    JOIN funcoes f ON f.id = u.funcao_id
                    WHERE LOWER(u.email) = LOWER(%s)
                    LIMIT 1;
                    """,
                    (email_limpo,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                if not _verificar_senha(row[5], senha):
                    return None
                return {
                    "id": row[0],
                    "nome": row[1],
                    "email": row[2],
                    "cpf": row[3] or "",
                    "instituicao": row[4] or "",
                    "funcao_id": row[6],
                    "funcao": row[7],
                }

    @staticmethod
    def buscar_por_id(usuario_id: int):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT u.id, u.nome, u.email, u.cpf, u.instituicao,
                           u.funcao_id, f.descricao
                    FROM usuarios u
                    JOIN funcoes f ON f.id = u.funcao_id
                    WHERE u.id = %s
                    LIMIT 1;
                    """,
                    (usuario_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "id": row[0],
                    "nome": row[1],
                    "email": row[2],
                    "cpf": row[3] or "",
                    "instituicao": row[4] or "",
                    "funcao_id": row[5],
                    "funcao": row[6],
                }

    @staticmethod
    def criar(nome: str, email: str, cpf: str, instituicao: str, senha: str) -> int:
        nome = (nome or "").strip()
        instituicao = (instituicao or "").strip()

        if not nome or not instituicao or not senha:
            raise ValueError("Preencha todos os campos obrigatórios.")
        if len(nome) > 100:
            raise ValueError("O nome completo deve ter no máximo 100 caracteres.")
        if len(instituicao) > 150:
            raise ValueError("A instituição/campus deve ter no máximo 150 caracteres.")
        if len(senha) < 6 or len(senha) > 50:
            raise ValueError("A senha deve ter entre 6 e 50 caracteres.")

        email_limpo = _validar_email(email)
        cpf_formatado = _formatar_cpf(cpf)
        senha_hash = generate_password_hash(senha)

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM usuarios WHERE LOWER(email) = LOWER(%s) LIMIT 1;",
                    (email_limpo,),
                )
                if cur.fetchone():
                    raise ValueError("E-mail já cadastrado.")

                cur.execute(
                    "SELECT id FROM usuarios WHERE cpf = %s LIMIT 1;",
                    (cpf_formatado,),
                )
                if cur.fetchone():
                    raise ValueError("CPF já cadastrado.")

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
                    INSERT INTO usuarios (funcao_id, nome, email, cpf, instituicao, senha)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (funcao_id, nome, email_limpo, cpf_formatado, instituicao, senha_hash),
                )
                novo_id = cur.fetchone()[0]
            conn.commit()
            return novo_id

    @staticmethod
    def atualizar(
        usuario_id: int,
        nome: str,
        email: str,
        cpf: str,
        instituicao: str,
        nova_senha: str = "",
    ) -> bool:
        nome = (nome or "").strip()
        instituicao = (instituicao or "").strip()
        nova_senha = nova_senha or ""

        if not nome or not instituicao:
            raise ValueError("Preencha nome completo, e-mail, CPF e instituição/campus.")
        if len(nome) > 100:
            raise ValueError("O nome completo deve ter no máximo 100 caracteres.")
        if len(instituicao) > 150:
            raise ValueError("A instituição/campus deve ter no máximo 150 caracteres.")
        if nova_senha and (len(nova_senha) < 6 or len(nova_senha) > 50):
            raise ValueError("A nova senha deve ter entre 6 e 50 caracteres.")

        email_limpo = _validar_email(email)
        cpf_formatado = _formatar_cpf(cpf)

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT email FROM usuarios WHERE id = %s LIMIT 1;",
                    (usuario_id,),
                )
                atual_row = cur.fetchone()
                if not atual_row:
                    return False
                email_antigo = atual_row[0]

                cur.execute(
                    "SELECT id FROM usuarios WHERE LOWER(email) = LOWER(%s) AND id <> %s LIMIT 1;",
                    (email_limpo, usuario_id),
                )
                if cur.fetchone():
                    raise ValueError("Este e-mail já está em uso por outro usuário.")

                cur.execute(
                    "SELECT id FROM usuarios WHERE cpf = %s AND id <> %s LIMIT 1;",
                    (cpf_formatado, usuario_id),
                )
                if cur.fetchone():
                    raise ValueError("Este CPF já está em uso por outro usuário.")

                if nova_senha:
                    cur.execute(
                        """
                        UPDATE usuarios
                        SET nome = %s, email = %s, cpf = %s, instituicao = %s, senha = %s
                        WHERE id = %s;
                        """,
                        (
                            nome,
                            email_limpo,
                            cpf_formatado,
                            instituicao,
                            generate_password_hash(nova_senha),
                            usuario_id,
                        ),
                    )
                else:
                    cur.execute(
                        """
                        UPDATE usuarios
                        SET nome = %s, email = %s, cpf = %s, instituicao = %s
                        WHERE id = %s;
                        """,
                        (nome, email_limpo, cpf_formatado, instituicao, usuario_id),
                    )
                atualizado = cur.rowcount > 0

                # Mantém os trabalhos já submetidos vinculados caso o usuário troque de e-mail
                if email_antigo and email_antigo.lower() != email_limpo.lower():
                    cur.execute(
                        "UPDATE autores SET email = %s WHERE LOWER(email) = LOWER(%s);",
                        (email_limpo, email_antigo),
                    )
            conn.commit()
            return atualizado

    @staticmethod
    def listar_todos() -> list[dict]:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT u.id, u.nome, u.email, u.cpf, u.instituicao,
                           u.funcao_id, f.descricao
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
                        "cpf": r[3] or "",
                        "instituicao": r[4] or "",
                        "funcao_id": r[5],
                        "funcao": r[6],
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
