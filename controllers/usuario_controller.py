from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from models.formulario import Formulario
from models.usuario import Usuario

usuario_bp = Blueprint("usuario", __name__)


@usuario_bp.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        form_atual = {
            "nome": request.form.get("nome", "").strip(),
            "email": request.form.get("email", "").strip(),
            "cpf": request.form.get("cpf", "").strip(),
            "instituicao": request.form.get("instituicao", "").strip(),
        }
        senha = request.form.get("senha", "")

        try:
            novo_id = Usuario.criar(
                nome=form_atual["nome"],
                email=form_atual["email"],
                cpf=form_atual["cpf"],
                instituicao=form_atual["instituicao"],
                senha=senha,
            )
        except ValueError as erro:
            flash(str(erro))
            return render_template("cadastro.html", form_atual=form_atual), 400

        session["usuario_id"] = novo_id
        session["usuario_nome"] = form_atual["nome"]
        session["usuario_email"] = form_atual["email"]
        session["usuario_funcao"] = "normal"

        flash("Cadastro realizado com sucesso!")
        return redirect(url_for("dashboard"))

    return render_template("cadastro.html", form_atual={})


@usuario_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "")

        usuario = Usuario.autenticar(email, senha)
        if not usuario:
            flash("E-mail ou senha incorretos.")
            return render_template("login.html", email_atual=email), 401

        session["usuario_id"] = usuario["id"]
        session["usuario_nome"] = usuario["nome"]
        session["usuario_email"] = usuario["email"]
        session["usuario_funcao"] = usuario["funcao"]

        flash(f"Bem-vindo(a), {usuario['nome']}!")
        if (usuario["funcao"] or "").lower() == "admin":
            return redirect("/avaliador")
        return redirect(url_for("dashboard"))

    return render_template("login.html", email_atual="")


@usuario_bp.route("/logout")
def logout():
    session.pop("usuario_id", None)
    session.pop("usuario_nome", None)
    session.pop("usuario_email", None)
    session.pop("usuario_funcao", None)
    flash("Você saiu da sua conta.")
    return redirect(url_for("index"))


@usuario_bp.route("/perfil", methods=["GET", "POST"])
def perfil():
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        flash("Faça login para editar seus dados.")
        return redirect(url_for("login"))

    if request.method == "POST":
        dados_form = {
            "nome": request.form.get("nome", "").strip(),
            "email": request.form.get("email", "").strip(),
            "cpf": request.form.get("cpf", "").strip(),
            "instituicao": request.form.get("instituicao", "").strip(),
        }
        nova_senha = request.form.get("nova_senha", "")

        try:
            atualizado = Usuario.atualizar(
                usuario_id=usuario_id,
                nome=dados_form["nome"],
                email=dados_form["email"],
                cpf=dados_form["cpf"],
                instituicao=dados_form["instituicao"],
                nova_senha=nova_senha,
            )
            if not atualizado:
                flash("Usuário não encontrado.")
                return redirect(url_for("logout"))
        except ValueError as erro:
            flash(str(erro))
            return render_template("editar_usuario.html", usuario=dados_form), 400

        session["usuario_nome"] = dados_form["nome"]
        session["usuario_email"] = dados_form["email"]
        flash("Dados cadastrais atualizados com sucesso!")
        return redirect(url_for("perfil"))

    usuario = Usuario.buscar_por_id(usuario_id)
    if not usuario:
        session.clear()
        flash("Usuário não encontrado.")
        return redirect(url_for("login"))

    return render_template("editar_usuario.html", usuario=usuario)


@usuario_bp.route("/dashboard")
def dashboard():
    if not session.get("usuario_id"):
        flash("Faça login para visualizar seus trabalhos.")
        return redirect(url_for("login"))

    email_usuario = session.get("usuario_email", "")
    trabalhos = Formulario.listar_por_email_autor(email_usuario)
    return render_template("dashboard.html", trabalhos=trabalhos)
