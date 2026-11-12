class Instituicao:
    @staticmethod
    def validar_dados(dados: dict) -> dict:
        nome = (dados.get("nome") or "").strip()
        cidade = (dados.get("cidade") or "").strip()

        if not (nome and cidade):
            raise ValueError("Preencha todos os campos da instituição.")
        if len(nome) > 255:
            raise ValueError("O nome da instituição deve ter no máximo 255 caracteres.")
        if len(cidade) > 100:
            raise ValueError("A cidade da instituição deve ter no máximo 100 caracteres.")

        return {"nome": nome, "cidade": cidade}

    @staticmethod
    def obter_ou_criar(cur, nome: str, cidade: str) -> int:
        cur.execute(
            """
            SELECT id FROM instituicoes
            WHERE LOWER(nome) = LOWER(%s)
              AND LOWER(cidade) = LOWER(%s)
            LIMIT 1;
            """,
            (nome, cidade),
        )
        row = cur.fetchone()
        if row:
            return row[0]

        cur.execute(
            """
            INSERT INTO instituicoes (nome, cidade)
            VALUES (%s, %s)
            RETURNING id;
            """,
            (nome, cidade),
        )
        return cur.fetchone()[0]
