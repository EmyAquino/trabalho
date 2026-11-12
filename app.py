import os
import secrets
import sys
from flask import Flask, flash, redirect, render_template, request, session, url_for
import database.database as database
from controllers import formulario_bp, usuario_bp
from controllers.formulario_controller import (
    arquivo,
    atualizar_status,
    avaliador,
    detalhe,
    formulario,
    index,
)
from controllers.usuario_controller import cadastro, dashboard, login, logout, perfil


def create_app(testing: bool = False) -> Flask:
    flask_app = Flask(__name__)
    flask_app.secret_key = os.environ.get("SECRET_KEY", "troque-esta-chave")
    flask_app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # limite de 10 MB
    flask_app.config["TESTING"] = testing

    if not testing:
        try:
            database.init_db()
        except Exception as exc:
            flask_app.logger.warning("Aviso ao inicializar banco PostgreSQL: %s", exc)

    def gerar_csrf_token() -> str:
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_hex(16)
        return session["csrf_token"]

    @flask_app.context_processor
    def injetar_csrf():
        return {"csrf_token": gerar_csrf_token}

    @flask_app.template_filter("formatar_data")
    def formatar_data(valor):
        if not valor:
            return "-"
        if hasattr(valor, "strftime"):
            return valor.strftime("%d/%m/%Y %H:%M")
        return str(valor)

    @flask_app.before_request
    def verificar_csrf():
        if request.method == "POST":
            token_sessao = session.get("csrf_token")
            token_form = request.form.get("csrf_token")
            if not token_sessao or not token_form or token_sessao != token_form:
                return (
                    render_template(
                        "404.html",
                        titulo_erro="400 - Requisição inválida",
                        mensagem_erro="Sessão expirada ou token CSRF inválido. Volte e tente novamente.",
                    ),
                    400,
                )

    flask_app.register_blueprint(formulario_bp)
    flask_app.register_blueprint(usuario_bp)

    flask_app.add_url_rule("/", endpoint="index", view_func=index)
    flask_app.add_url_rule(
        "/formulario", endpoint="formulario", view_func=formulario, methods=["GET", "POST"]
    )
    flask_app.add_url_rule("/trabalho/<int:id>", endpoint="detalhe", view_func=detalhe)
    flask_app.add_url_rule("/trabalho/<int:id>/arquivo", endpoint="arquivo", view_func=arquivo)

    flask_app.add_url_rule(
        "/cadastro", endpoint="cadastro", view_func=cadastro, methods=["GET", "POST"]
    )
    flask_app.add_url_rule(
        "/login", endpoint="login", view_func=login, methods=["GET", "POST"]
    )
    flask_app.add_url_rule("/logout", endpoint="logout", view_func=logout)
    flask_app.add_url_rule(
        "/perfil", endpoint="perfil", view_func=perfil, methods=["GET", "POST"]
    )
    flask_app.add_url_rule("/dashboard", endpoint="dashboard", view_func=dashboard)
    flask_app.add_url_rule("/avaliador", endpoint="avaliador", view_func=avaliador)
    flask_app.add_url_rule(
        "/avaliador/status/<int:id>",
        endpoint="atualizar_status",
        view_func=atualizar_status,
        methods=["POST"],
    )

    @flask_app.errorhandler(404)
    def pagina_nao_encontrada(_erro):
        return render_template("404.html"), 404

    @flask_app.errorhandler(500)
    def erro_interno(_erro):
        return render_template("500.html"), 500

    @flask_app.errorhandler(413)
    def arquivo_grande(_erro):
        flash("Arquivo muito grande (máximo de 10 MB).")
        return redirect(url_for("formulario"))

    return flask_app


app = create_app(
    testing=os.environ.get("FLASK_TESTING") == "1" or "pytest" in sys.modules
)

if __name__ == "__main__":
    app.run(debug=True)
