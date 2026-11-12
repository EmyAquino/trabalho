from contextlib import contextmanager
from datetime import datetime
import pytest
from werkzeug.security import generate_password_hash

import database.database as db
from models.autor import Autor
from models.formulario import Formulario
from models.usuario import Usuario


class CursorFalso:
    def __init__(self, respostas=None):
        self.respostas = list(respostas or [])
        self.queries = []
        self.rowcount = 1

    def execute(self, sql, params=None):
        self.queries.append((sql, params))

    def fetchone(self):
        if self.respostas:
            return self.respostas.pop(0)
        return None

    def fetchall(self):
        if self.respostas:
            return self.respostas.pop(0)
        return []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class ConexaoFalsa:
    def __init__(self, cursor):
        self._cursor = cursor
        self.comitou = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.comitou = True


def usar_banco_falso(monkeypatch, modulo, respostas):
    cur = CursorFalso(respostas)
    conn = ConexaoFalsa(cur)

    @contextmanager
    def _fake_conn():
        yield conn

    monkeypatch.setattr(modulo, "get_connection", _fake_conn)
    return cur, conn


def test_init_db_executa_migracoes_e_cria_avaliador_padrao(monkeypatch):
    # Respostas: funcoes Admin/normal, modalidades (3), checagem avaliador (None), busca funcao Admin ((1,))
    cur, conn = usar_banco_falso(
        monkeypatch,
        db,
        respostas=[(1,), (2,), (1,), (2,), (3,), None, (1,)],
    )
    db.init_db()
    sql_completo = "\n".join(q[0] for q in cur.queries)
    assert "ADD COLUMN IF NOT EXISTS cpf" in sql_completo
    assert "ADD COLUMN IF NOT EXISTS instituicao" in sql_completo
    assert "ADD COLUMN IF NOT EXISTS data_envio" in sql_completo
    assert "ADD COLUMN IF NOT EXISTS status" in sql_completo
    inserts_avaliador = [
        q[1] for q in cur.queries if "INSERT INTO usuarios" in q[0]
    ]
    assert inserts_avaliador
    cpf_seed = inserts_avaliador[0][3]
    # O CPF do seed precisa passar na validacao ao editar o perfil
    from models.usuario import _formatar_cpf

    assert _formatar_cpf(cpf_seed) == cpf_seed
    assert conn.comitou is True


def test_usuario_criar_valida_campos_e_formata_cpf(monkeypatch):
    # Respostas: email existe? None, cpf existe? None, funcao normal? (2,), insert returning id (10,)
    cur, conn = usar_banco_falso(monkeypatch, db, [])
    import models.usuario as mod_usuario

    cur, conn = usar_banco_falso(monkeypatch, mod_usuario, [None, None, (2,), (10,)])
    novo_id = Usuario.criar(
        "Maria da Silva",
        "maria@ifrs.edu.br",
        "12345678901",
        "IFRS - Campus Farroupilha",
        "senha123",
    )
    assert novo_id == 10
    assert conn.comitou is True
    sql_insert, params_insert = cur.queries[-1]
    assert "cpf" in sql_insert and "instituicao" in sql_insert
    assert "123.456.789-01" in params_insert
    # A senha salva deve estar com hash, nunca em texto puro
    assert "senha123" not in params_insert


def test_usuario_criar_rejeita_dados_invalidos(monkeypatch):
    import models.usuario as mod_usuario

    usar_banco_falso(monkeypatch, mod_usuario, [])

    with pytest.raises(ValueError, match="CPF"):
        Usuario.criar("Maria", "maria@ifrs.edu.br", "123", "IFRS", "senha123")

    with pytest.raises(ValueError, match="CPF"):
        Usuario.criar("Maria", "maria@ifrs.edu.br", "111.111.111-11", "IFRS", "senha123")

    with pytest.raises(ValueError, match="e-mail"):
        Usuario.criar("Maria", "email-invalido", "12345678901", "IFRS", "senha123")

    with pytest.raises(ValueError, match="senha"):
        Usuario.criar("Maria", "maria@ifrs.edu.br", "12345678901", "IFRS", "123")


def test_usuario_autenticar_aceita_hash_e_texto_puro_legado(monkeypatch):
    import models.usuario as mod_usuario

    hash_senha = generate_password_hash("minhasenha")
    linha_hash = (
        1,
        "João",
        "joao@ifrs.edu.br",
        "123.456.789-01",
        "IFRS",
        hash_senha,
        2,
        "normal",
    )
    usar_banco_falso(monkeypatch, mod_usuario, [linha_hash])
    user = Usuario.autenticar("joao@ifrs.edu.br", "minhasenha")
    assert user is not None
    assert user["cpf"] == "123.456.789-01"
    assert user["instituicao"] == "IFRS"

    # Legado em texto puro já salvo no banco antigo
    linha_legada = (2, "Antigo", "antigo@ifrs.edu.br", "", "", "123456", 2, "normal")
    usar_banco_falso(monkeypatch, mod_usuario, [linha_legada])
    user_legado = Usuario.autenticar("antigo@ifrs.edu.br", "123456")
    assert user_legado is not None
    assert user_legado["id"] == 2


def test_usuario_atualizar_sincroniza_email_autor_e_preserva_senha_vazia(monkeypatch):
    import models.usuario as mod_usuario

    # Respostas: usuario atual (email antigo), email duplicado? None, cpf duplicado? None
    cur, conn = usar_banco_falso(
        monkeypatch,
        mod_usuario,
        [("antigo@ifrs.edu.br",), None, None],
    )
    ok = Usuario.atualizar(
        usuario_id=5,
        nome="Maria Atualizada",
        email="novo@ifrs.edu.br",
        cpf="123.456.789-01",
        instituicao="IFRS - Bento",
        nova_senha="",
    )
    assert ok is True
    assert conn.comitou is True
    sqls = "\n".join(q[0] for q in cur.queries)
    assert "UPDATE usuarios" in sqls
    assert "senha =" not in sqls  # não trocou senha vazia
    assert "UPDATE autores SET email" in sqls


def test_formulario_listar_por_autor_e_atualizar_status(monkeypatch):
    import models.formulario as mod_form

    agora = datetime(2026, 11, 12, 19, 0)
    linha = (
        7,
        "Meu Artigo",
        "Resumo teste",
        "IA",
        "Engenharias",
        agora,
        "Pendente",
        1,
        "Pesquisa",
        3,
        "Maria",
        "maria@ifrs.edu.br",
        "Computação",
        "Farroupilha",
        2,
        "IFRS - Farroupilha",
        "Farroupilha",
    )
    usar_banco_falso(monkeypatch, mod_form, [[linha]])
    lista = Formulario.listar_por_email_autor("maria@ifrs.edu.br")
    assert len(lista) == 1
    assert lista[0]["status"] == "Pendente"
    assert lista[0]["data_envio"] == agora

    cur, conn = usar_banco_falso(monkeypatch, mod_form, [])
    assert Formulario.atualizar_status(7, "Aprovado") is True
    assert conn.comitou is True

    with pytest.raises(ValueError, match="Status inválido"):
        Formulario.atualizar_status(7, "Inventado")


def test_validacoes_extras_autor_e_resumo():
    with pytest.raises(ValueError, match="e-mail"):
        Autor.validar_dados(
            {"nome": "João", "email": "sem-arroba", "area": "TI", "cidade": "POA"}
        )

    with pytest.raises(ValueError, match="1000"):
        Formulario._validar_dados_form(
            {
                "titulo": "Teste",
                "resumo": "a" * 1001,
                "palavra_chave": "teste",
                "area_conhecimento": "Engenharias",
                "modalidade_id": 1,
            }
        )
