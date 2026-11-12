import io
from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from werkzeug.utils import secure_filename
from models.formulario import Formulario
from models.modalidade import Modalidade

formulario_bp = Blueprint("formulario", __name__)


def _ler_pdf(arquivo) -> bytes:
    if not arquivo or not arquivo.filename:
        raise ValueError("O envio do arquivo PDF é obrigatório.")
    nome_original = secure_filename(arquivo.filename)
    if not nome_original.lower().endswith(".pdf"):
        raise ValueError("O arquivo precisa ser um PDF.")
    dados = arquivo.read()
    if not dados:
        raise ValueError("O arquivo enviado está vazio.")
    if not dados.startswith(b"%PDF"):
        raise ValueError("O arquivo enviado não é um PDF válido.")
    return dados


def _resolver_modalidade_id(valor_modalidade: str):
    valor = (valor_modalidade or "").strip()
    if not valor:
        return None
    if valor.isdigit():
        mod = Modalidade.buscar_por_id(int(valor))
        return mod["id"] if mod else None
    mod = Modalidade.buscar_por_descricao(valor)
    return mod["id"] if mod else None


def _verificar_acesso_avaliador():
    if not session.get("usuario_id"):
        flash("Faça login como avaliador para acessar este painel.")
        return redirect(url_for("login"))
    if (session.get("usuario_funcao") or "").lower() != "admin":
        flash("Acesso restrito aos avaliadores.")
        return redirect(url_for("index"))
    return None


@formulario_bp.route("/")
def index():
    trabalhos = Formulario.listar_todos()
    return render_template("index.html", trabalhos=trabalhos)


@formulario_bp.route("/formulario", methods=["GET", "POST"])
def formulario():
    modalidades = Modalidade.listar_todas()

    if request.method == "POST":
        instituicao_sigla = request.form.get("instituicao", "").strip()
        campus = request.form.get("campus", "").strip()
        if instituicao_sigla and campus:
            instituicao_nome = f"{instituicao_sigla} - {campus}"
        else:
            instituicao_nome = instituicao_sigla or campus

        dados_autor = {
            "nome": (request.form.get("autor") or request.form.get("autor_nome") or "").strip(),
            "email": request.form.get("autor_email", "").strip(),
            "area": request.form.get("autor_area", "").strip(),
            "cidade": request.form.get("autor_cidade", "").strip(),
        }
        dados_instituicao = {
            "nome": instituicao_nome,
            "cidade": request.form.get("instituicao_cidade", "").strip(),
        }
        palavra_chave = (
            request.form.get("palavras_chave") or request.form.get("palavra_chave") or ""
        ).strip()
        modalidade_raw = (
            request.form.get("modalidade") or request.form.get("modalidade_id") or ""
        ).strip()

        form_atual = {
            "titulo": request.form.get("titulo", "").strip(),
            "autor": dados_autor["nome"],
            "autor_email": dados_autor["email"],
            "autor_area": dados_autor["area"],
            "autor_cidade": dados_autor["cidade"],
            "instituicao": instituicao_sigla,
            "campus": campus,
            "instituicao_cidade": dados_instituicao["cidade"],
            "resumo": request.form.get("resumo", "").strip(),
            "palavras_chave": palavra_chave,
            "area_conhecimento": request.form.get("area_conhecimento", "").strip(),
            "modalidade": modalidade_raw,
        }

        modalidade_id = _resolver_modalidade_id(modalidade_raw)
        if not modalidade_id:
            flash("Preencha todos os campos e escolha uma modalidade válida.")
            return (
                render_template(
                    "formulario.html", modalidades=modalidades, form_atual=form_atual
                ),
                400,
            )

        dados_form = {
            "modalidade_id": modalidade_id,
            "titulo": form_atual["titulo"],
            "resumo": form_atual["resumo"],
            "palavra_chave": palavra_chave,
            "area_conhecimento": form_atual["area_conhecimento"],
        }

        try:
            arquivo_bytes = _ler_pdf(request.files.get("arquivo"))
            Formulario.criar(
                dados_autor=dados_autor,
                dados_instituicao=dados_instituicao,
                dados_form=dados_form,
                arquivo_bytes=arquivo_bytes,
            )
        except ValueError as erro:
            flash(str(erro))
            return (
                render_template(
                    "formulario.html", modalidades=modalidades, form_atual=form_atual
                ),
                400,
            )

        flash("Trabalho enviado com sucesso!")
        return redirect(url_for("index"))

    form_inicial = {}
    if session.get("usuario_id"):
        form_inicial = {
            "autor": session.get("usuario_nome", ""),
            "autor_email": session.get("usuario_email", ""),
        }

    return render_template("formulario.html", modalidades=modalidades, form_atual=form_inicial)


@formulario_bp.route("/trabalho/<int:id>")
def detalhe(id: int):
    trabalho = Formulario.buscar_por_id(id)
    if not trabalho:
        abort(404)
    return render_template("detalhe.html", t=trabalho)


@formulario_bp.route("/trabalho/<int:id>/arquivo")
def arquivo(id: int):
    resultado = Formulario.buscar_arquivo(id)
    if not resultado:
        abort(404)
    arquivo_bytes, titulo = resultado
    nome_download = secure_filename(f"{titulo}.pdf") or f"trabalho_{id}.pdf"
    return send_file(
        io.BytesIO(arquivo_bytes),
        mimetype="application/pdf",
        as_attachment=False,
        download_name=nome_download,
    )


@formulario_bp.route("/avaliador")
def avaliador():
    bloqueio = _verificar_acesso_avaliador()
    if bloqueio:
        return bloqueio

    trabalhos = Formulario.listar_todos()
    return render_template("avaliador.html", trabalhos=trabalhos)


@formulario_bp.route("/avaliador/status/<int:id>", methods=["POST"])
def atualizar_status(id: int):
    bloqueio = _verificar_acesso_avaliador()
    if bloqueio:
        return bloqueio

    novo_status = request.form.get("status", "").strip()
    try:
        atualizado = Formulario.atualizar_status(id, novo_status)
    except ValueError as erro:
        flash(str(erro))
        trabalhos = Formulario.listar_todos()
        return render_template("avaliador.html", trabalhos=trabalhos), 400

    if not atualizado:
        abort(404)

    flash(f"Status do trabalho atualizado para {novo_status}.")
    return redirect(url_for("avaliador"))
