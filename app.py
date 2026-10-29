from flask import Flask, render_template, request, redirect, url_for, flash, abort

app = Flask(__name__)
app.secret_key = "troque-esta-chave"  # necessária para flash()

MODALIDADES = ["Ensino", "Pesquisa", "Extensão"]

# "Banco de dados" em memória, já com alguns dados para teste
trabalhos = [
    {
        "titulo": "Teoria Quântica",
        "autor": "Fulano",
        "campus": "IFRS - Campus Farroupilha",
        "modalidade": "Pesquisa",
        "resumo": "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
    },
    {
        "titulo": "Horta Escolar Sustentável",
        "autor": "Beltrana",
        "campus": "IFRS - Campus Bento Gonçalves",
        "modalidade": "Extensão",
        "resumo": "Projeto de extensão que envolve a comunidade escolar na criação e manutenção de uma horta, com oficinas sobre alimentação saudável e compostagem.",
    },
    {
        "titulo": "Metodologias Ativas no Ensino Técnico",
        "autor": "Ciclano",
        "campus": "IFRS - Campus Caxias do Sul",
        "modalidade": "Ensino",
        "resumo": "Relato de experiência sobre a aplicação de aprendizagem baseada em projetos em turmas do curso técnico integrado.",
    },
]


@app.route("/")
def index():
    return render_template("index.html", trabalhos=trabalhos)


@app.route("/formulario", methods=["GET", "POST"])
def formulario():
    if request.method == "POST":
        trabalhos.append({
            "titulo": request.form["titulo"].strip(),
            "autor": request.form["autor"].strip(),
            "campus": request.form["campus"].strip(),
            "resumo": request.form["resumo"].strip(),
            "modalidade": request.form["modalidade"],
        })
        flash("Trabalho enviado com sucesso!")
        return redirect(url_for("index"))
    return render_template("formulario.html", modalidades=MODALIDADES)


@app.route("/trabalho/<int:id>")
def detalhe(id):
    if id < 0 or id >= len(trabalhos):
        abort(404)
    return render_template("detalhe.html", t=trabalhos[id])


if __name__ == "__main__":
    app.run(debug=True)
