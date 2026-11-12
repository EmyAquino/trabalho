import os
import sys
from flask import Flask, flash, redirect, url_for
import database.database as database
from controllers import formulario_bp
from controllers.formulario_controller import arquivo, detalhe, formulario, index


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

    flask_app.register_blueprint(formulario_bp)
    flask_app.add_url_rule("/", endpoint="index", view_func=index)
    flask_app.add_url_rule(
        "/formulario", endpoint="formulario", view_func=formulario, methods=["GET", "POST"]
    )
    flask_app.add_url_rule("/trabalho/<int:id>", endpoint="detalhe", view_func=detalhe)
    flask_app.add_url_rule("/trabalho/<int:id>/arquivo", endpoint="arquivo", view_func=arquivo)

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
