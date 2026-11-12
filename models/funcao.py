from database import get_connection


class Funcao:
    @staticmethod
    def listar_todas() -> list[dict]:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, descricao FROM funcoes ORDER BY id;")
                return [{"id": r[0], "descricao": r[1]} for r in cur.fetchall()]

    @staticmethod
    def buscar_por_descricao(descricao: str) -> dict | None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, descricao FROM funcoes WHERE LOWER(descricao) = LOWER(%s) LIMIT 1;",
                    (descricao,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return {"id": row[0], "descricao": row[1]}
