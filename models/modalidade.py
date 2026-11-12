from database.database import get_connection


class Modalidade:
    @staticmethod
    def listar_todas() -> list[dict]:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, descricao FROM modalidades_formularios ORDER BY id;")
                return [{"id": r[0], "descricao": r[1]} for r in cur.fetchall()]

    @staticmethod
    def buscar_por_id(modalidade_id: int) -> dict | None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, descricao FROM modalidades_formularios WHERE id = %s;",
                    (modalidade_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return {"id": row[0], "descricao": row[1]}

    @staticmethod
    def buscar_por_descricao(descricao: str) -> dict | None:
        termo = (descricao or "").strip()
        if termo.lower() == "extensao":
            termo = "Extensão"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, descricao FROM modalidades_formularios WHERE LOWER(descricao) = LOWER(%s) LIMIT 1;",
                    (termo,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return {"id": row[0], "descricao": row[1]}
