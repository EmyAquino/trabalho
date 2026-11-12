from datetime import datetime
import pytest

from app import create_app
from models.formulario import Formulario
from models.usuario import Usuario


@pytest.fixture
def cliente():
    flask_app = create_app(testing=True)
    flask_app.config["PROPAGATE_EXCEPTIONS"] = False

    @flask_app.route("/forcar-erro-500")
    def _erro_500():
        raise RuntimeError("Falha simulada")

    return flask_app.test_client()


def obter_csrf(cliente) -> str:
    with cliente.session_transaction() as sess:
        sess["csrf_token"] = "token-teste-123"
    return "token-teste-123"


def test_csrf_bloqueia_post_sem_token(cliente):
    resp = cliente.post("/login", data={"email": "a@b.com", "senha": "123456"})
    assert resp.status_code == 400
    texto = resp.get_data(as_text=True)
    assert "CSRF" in texto or "inválido" in texto.lower() or "expirada" in texto.lower()


def test_paginas_personalizadas_404_e_500(cliente):
    resp_404 = cliente.get("/rota-que-nao-existe-mesmo")
    assert resp_404.status_code == 404
    html_404 = resp_404.get_data(as_text=True)
    assert "404" in html_404
    assert "não encontrada" in html_404.lower()

    resp_500 = cliente.get("/forcar-erro-500")
    assert resp_500.status_code == 500
    html_500 = resp_500.get_data(as_text=True)
    assert "500" in html_500
    assert "erro interno" in html_500.lower()


def test_cadastro_usuario_fluxo_completo(cliente, monkeypatch):
    pagina = cliente.get("/cadastro")
    assert pagina.status_code == 200
    html = pagina.get_data(as_text=True)
    assert 'name="csrf_token"' in html
    assert 'name="cpf"' in html
    assert 'name="instituicao"' in html

    token = obter_csrf(cliente)

    # Erro de validação
    monkeypatch.setattr(
        Usuario,
        "criar",
        staticmethod(lambda *a, **kw: (_ for _ in ()).throw(ValueError("CPF inválido."))),
    )
    resp_erro = cliente.post(
        "/cadastro",
        data={
            "csrf_token": token,
            "nome": "Ana Souza",
            "email": "ana@ifrs.edu.br",
            "cpf": "111",
            "instituicao": "IFRS - Farroupilha",
            "senha": "senha123",
        },
    )
    assert resp_erro.status_code == 400
    assert "CPF inválido." in resp_erro.get_data(as_text=True)

    # Cadastro válido
    monkeypatch.setattr(Usuario, "criar", staticmethod(lambda *a, **kw: 42))
    resp_ok = cliente.post(
        "/cadastro",
        data={
            "csrf_token": token,
            "nome": "Ana Souza",
            "email": "ana@ifrs.edu.br",
            "cpf": "12345678901",
            "instituicao": "IFRS - Farroupilha",
            "senha": "senha123",
        },
    )
    assert resp_ok.status_code == 302
    assert "/dashboard" in resp_ok.headers["Location"]
    with cliente.session_transaction() as sess:
        assert sess["usuario_id"] == 42
        assert sess["usuario_email"] == "ana@ifrs.edu.br"


def test_login_logout_redirecionamentos(cliente, monkeypatch):
    token = obter_csrf(cliente)

    monkeypatch.setattr(Usuario, "autenticar", staticmethod(lambda e, s: None))
    resp_falha = cliente.post(
        "/login", data={"csrf_token": token, "email": "x@y.com", "senha": "errada"}
    )
    assert resp_falha.status_code == 401
    assert "incorretos" in resp_falha.get_data(as_text=True).lower()

    monkeypatch.setattr(
        Usuario,
        "autenticar",
        staticmethod(
            lambda e, s: {
                "id": 1,
                "nome": "Avaliador",
                "email": "avaliador@ifrs.edu.br",
                "cpf": "000.000.000-00",
                "instituicao": "IFRS",
                "funcao_id": 1,
                "funcao": "Admin",
            }
        ),
    )
    resp_admin = cliente.post(
        "/login",
        data={"csrf_token": token, "email": "avaliador@ifrs.edu.br", "senha": "admin123"},
    )
    assert resp_admin.status_code == 302
    assert "/avaliador" in resp_admin.headers["Location"]

    resp_sair = cliente.get("/logout")
    assert resp_sair.status_code == 302
    with cliente.session_transaction() as sess:
        assert "usuario_id" not in sess


def test_edicao_perfil_exige_login_e_atualiza_sessao(cliente, monkeypatch):
    sem_login = cliente.get("/perfil")
    assert sem_login.status_code == 302
    assert "/login" in sem_login.headers["Location"]

    token = obter_csrf(cliente)
    with cliente.session_transaction() as sess:
        sess["usuario_id"] = 9
        sess["usuario_nome"] = "Carlos"
        sess["usuario_email"] = "carlos@ifrs.edu.br"
        sess["usuario_funcao"] = "normal"

    monkeypatch.setattr(
        Usuario,
        "buscar_por_id",
        staticmethod(
            lambda uid: {
                "id": uid,
                "nome": "Carlos",
                "email": "carlos@ifrs.edu.br",
                "cpf": "123.456.789-01",
                "instituicao": "IFRS - Caxias",
                "funcao_id": 2,
                "funcao": "normal",
            }
        ),
    )
    pagina = cliente.get("/perfil")
    assert pagina.status_code == 200
    assert "IFRS - Caxias" in pagina.get_data(as_text=True)

    chamado = {}

    def _fake_atualizar(usuario_id, nome, email, cpf, instituicao, nova_senha=""):
        chamado["email"] = email
        chamado["nome"] = nome
        return True

    monkeypatch.setattr(Usuario, "atualizar", staticmethod(_fake_atualizar))
    resp_post = cliente.post(
        "/perfil",
        data={
            "csrf_token": token,
            "nome": "Carlos Silva",
            "email": "carlos.novo@ifrs.edu.br",
            "cpf": "123.456.789-01",
            "instituicao": "IFRS - Bento",
            "nova_senha": "",
        },
    )
    assert resp_post.status_code == 302
    assert chamado["email"] == "carlos.novo@ifrs.edu.br"
    with cliente.session_transaction() as sess:
        assert sess["usuario_email"] == "carlos.novo@ifrs.edu.br"
        assert sess["usuario_nome"] == "Carlos Silva"


def test_dashboard_autor_exibe_tabela_com_datas_e_status(cliente, monkeypatch):
    assert cliente.get("/dashboard").status_code == 302

    with cliente.session_transaction() as sess:
        sess["usuario_id"] = 9
        sess["usuario_nome"] = "Maria"
        sess["usuario_email"] = "maria@ifrs.edu.br"
        sess["usuario_funcao"] = "normal"

    monkeypatch.setattr(
        Formulario,
        "listar_por_email_autor",
        staticmethod(
            lambda email: [
                {
                    "id": 1,
                    "titulo": "Estudo sobre IA",
                    "modalidade": "Pesquisa",
                    "data_envio": datetime(2026, 11, 12, 14, 30),
                    "status": "Aprovado",
                },
                {
                    "id": 2,
                    "titulo": "Oficina de Robótica",
                    "modalidade": "Extensão",
                    "data_envio": None,
                    "status": "Pendente",
                },
            ]
        ),
    )

    resp = cliente.get("/dashboard")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "<table" in html
    assert "Estudo sobre IA" in html
    assert "Pesquisa" in html
    assert "12/11/2026" in html
    assert "Aprovado" in html
    assert "Oficina de Robótica" in html
    assert "Pendente" in html
