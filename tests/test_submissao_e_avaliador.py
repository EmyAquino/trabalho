import io
from datetime import datetime
import pytest

from app import create_app
from models.formulario import Formulario
from models.modalidade import Modalidade


@pytest.fixture
def cliente():
    flask_app = create_app(testing=True)
    return flask_app.test_client()


def definir_csrf(cliente) -> str:
    with cliente.session_transaction() as sess:
        sess["csrf_token"] = "csrf-submissao-123"
    return "csrf-submissao-123"


def test_listagem_detalhe_e_download_pdf(cliente, monkeypatch):
    trabalho_exemplo = {
        "id": 3,
        "titulo": "Projeto Solar",
        "resumo": "Resumo de energia solar no campus.",
        "palavra_chave": "Energia, Sustentabilidade",
        "area_conhecimento": "Engenharias",
        "data_envio": datetime(2026, 11, 12, 10, 0),
        "status": "Aprovado",
        "modalidade_id": 2,
        "modalidade": "Pesquisa",
        "autor_id": 1,
        "autor": "Lucas",
        "autor_nome": "Lucas",
        "autor_email": "lucas@ifrs.edu.br",
        "autor_area": "Elétrica",
        "autor_cidade": "Farroupilha",
        "instituicao_id": 1,
        "campus": "IFRS - Farroupilha",
        "instituicao_nome": "IFRS - Farroupilha",
        "instituicao_cidade": "Farroupilha",
    }

    monkeypatch.setattr(Formulario, "listar_todos", staticmethod(lambda: [trabalho_exemplo]))
    monkeypatch.setattr(
        Formulario,
        "buscar_por_id",
        staticmethod(lambda fid: trabalho_exemplo if fid == 3 else None),
    )
    monkeypatch.setattr(
        Formulario,
        "buscar_arquivo",
        staticmethod(lambda fid: (b"%PDF-1.4 conteudo", "Projeto Solar") if fid == 3 else None),
    )

    resp_index = cliente.get("/")
    assert resp_index.status_code == 200
    assert "Projeto Solar" in resp_index.get_data(as_text=True)

    resp_det = cliente.get("/trabalho/3")
    assert resp_det.status_code == 200
    html_det = resp_det.get_data(as_text=True)
    assert "Projeto Solar" in html_det
    assert "Aprovado" in html_det

    resp_pdf = cliente.get("/trabalho/3/arquivo")
    assert resp_pdf.status_code == 200
    assert resp_pdf.mimetype == "application/pdf"
    assert resp_pdf.data.startswith(b"%PDF")


def test_formulario_preenche_autor_logado_e_valida_pdf_e_csrf(cliente, monkeypatch):
    monkeypatch.setattr(
        Modalidade,
        "listar_todas",
        staticmethod(lambda: [{"id": 1, "descricao": "Ensino"}]),
    )
    monkeypatch.setattr(
        Modalidade,
        "buscar_por_descricao",
        staticmethod(lambda d: {"id": 1, "descricao": "Ensino"}),
    )

    with cliente.session_transaction() as sess:
        sess["usuario_id"] = 5
        sess["usuario_nome"] = "Bruna Costa"
        sess["usuario_email"] = "bruna@ifrs.edu.br"
        sess["usuario_funcao"] = "normal"

    get_resp = cliente.get("/formulario")
    assert get_resp.status_code == 200
    html = get_resp.get_data(as_text=True)
    assert 'name="csrf_token"' in html
    assert "Bruna Costa" in html
    assert "bruna@ifrs.edu.br" in html

    token = definir_csrf(cliente)
    dados_base = {
        "csrf_token": token,
        "titulo": "Monitoria de Algoritmos",
        "autor": "Bruna Costa",
        "autor_email": "bruna@ifrs.edu.br",
        "autor_area": "Computação",
        "autor_cidade": "Farroupilha",
        "instituicao": "IFRS",
        "campus": "Campus Farroupilha",
        "instituicao_cidade": "Farroupilha",
        "resumo": "Relato de monitoria.",
        "palavras_chave": "Ensino, Algoritmos",
        "area_conhecimento": "Ciencias Exatas e da Terra",
        "modalidade": "Ensino",
    }

    # Rejeita arquivo com extensão .pdf mas conteúdo falso
    dados_falso = dict(dados_base)
    dados_falso["arquivo"] = (io.BytesIO(b"isto nao eh um pdf"), "falso.pdf")
    resp_falso = cliente.post(
        "/formulario", data=dados_falso, content_type="multipart/form-data"
    )
    assert resp_falso.status_code == 400
    assert "pdf" in resp_falso.get_data(as_text=True).lower()

    # Aceita PDF real
    criado = {}

    def _fake_criar(**kwargs):
        criado.update(kwargs)
        return 11

    monkeypatch.setattr(Formulario, "criar", staticmethod(_fake_criar))
    dados_ok = dict(dados_base)
    dados_ok["arquivo"] = (io.BytesIO(b"%PDF-1.4 arquivo valido"), "artigo.pdf")
    resp_ok = cliente.post(
        "/formulario", data=dados_ok, content_type="multipart/form-data"
    )
    assert resp_ok.status_code == 302
    assert criado["dados_autor"]["email"] == "bruna@ifrs.edu.br"


def test_painel_avaliador_controle_acesso_e_alteracao_status(cliente, monkeypatch):
    token = definir_csrf(cliente)
    chamadas_status = []
    monkeypatch.setattr(
        Formulario,
        "atualizar_status",
        staticmethod(lambda fid, st: chamadas_status.append((fid, st)) or True),
    )

    # Usuário comum (normal) não pode acessar nem alterar status
    with cliente.session_transaction() as sess:
        sess["usuario_id"] = 2
        sess["usuario_nome"] = "Aluno"
        sess["usuario_email"] = "aluno@ifrs.edu.br"
        sess["usuario_funcao"] = "normal"

    assert cliente.get("/avaliador").status_code == 302
    resp_bloqueado = cliente.post(
        "/avaliador/status/7", data={"csrf_token": token, "status": "Aprovado"}
    )
    assert resp_bloqueado.status_code == 302
    assert chamadas_status == []

    # Usuário Admin (Avaliador) visualiza tudo e altera status
    with cliente.session_transaction() as sess:
        sess["usuario_id"] = 1
        sess["usuario_nome"] = "Avaliador"
        sess["usuario_email"] = "avaliador@ifrs.edu.br"
        sess["usuario_funcao"] = "Admin"

    monkeypatch.setattr(
        Formulario,
        "listar_todos",
        staticmethod(
            lambda: [
                {
                    "id": 7,
                    "titulo": "Artigo Avaliado",
                    "autor": "Maria",
                    "modalidade": "Pesquisa",
                    "data_envio": datetime(2026, 11, 12, 18, 0),
                    "status": "Pendente",
                }
            ]
        ),
    )

    pagina_aval = cliente.get("/avaliador")
    assert pagina_aval.status_code == 200
    html_aval = pagina_aval.get_data(as_text=True)
    assert "Artigo Avaliado" in html_aval
    assert "Reprovado" in html_aval

    resp_aprovar = cliente.post(
        "/avaliador/status/7", data={"csrf_token": token, "status": "Aprovado"}
    )
    assert resp_aprovar.status_code == 302
    assert chamadas_status == [(7, "Aprovado")]

    # Status inválido retorna 400 sem quebrar
    def _raise_invalido(fid, st):
        raise ValueError("Status inválido.")

    monkeypatch.setattr(Formulario, "atualizar_status", staticmethod(_raise_invalido))
    resp_inv = cliente.post(
        "/avaliador/status/7", data={"csrf_token": token, "status": "QualquerCoisa"}
    )
    assert resp_inv.status_code == 400
