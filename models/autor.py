class Autor:
    @staticmethod
    def validar_dados(dados: dict) -> dict:
        nome = (dados.get("nome") or "").strip()
        email = (dados.get("email") or "").strip()
        area = (dados.get("area") or "").strip()
        cidade = (dados.get("cidade") or "").strip()

        if not (nome and email and area and cidade):
            raise ValueError("Preencha todos os campos do autor.")
        if any(len(v) > 100 for v in (nome, email, area, cidade)):
            raise ValueError("Os campos do autor devem ter no máximo 100 caracteres.")

        return {"nome": nome, "email": email, "area": area, "cidade": cidade}

    @staticmethod
    def obter_ou_criar(cur, nome: str, email: str, area: str, cidade: str) -> int:
        cur.execute(
            """
            SELECT id FROM autores
            WHERE LOWER(email) = LOWER(%s)
              AND LOWER(nome) = LOWER(%s)
              AND LOWER(area) = LOWER(%s)
              AND LOWER(cidade) = LOWER(%s)
            LIMIT 1;
            """,
            (email, nome, area, cidade),
        )
        row = cur.fetchone()
        if row:
            return row[0]

        cur.execute(
            """
            INSERT INTO autores (nome, email, area, cidade)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
            """,
            (nome, email, area, cidade),
        )
        return cur.fetchone()[0]
