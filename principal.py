from flask import Flask, render_template, request
from pymongo import MongoClient
import os
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from bson.objectid import ObjectId


app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "./static/fondos"
EXTENSIONES = ["png", "jpg", "jpeg"]

def archivo_permitido(nombre):
    return "." in nombre and nombre.rsplit(".", 1)[1].lower() in EXTENSIONES

client = MongoClient("mongodb://localhost:27017")
basedatos = client.fondo
misfondos = basedatos.lista

TEMAS = ["animales", "naturaleza", "ciudad", "deporte", "personas"]

@app.route("/galeria")
@app.route("/")
def galeria():
    tema = request.args.get("tema")

    activo = {t: "" for t in ["todos"] + TEMAS}
    if tema:
        activo[tema] = "active"
        fondos = list(misfondos.find({"tags": tema.upper()}))
    else:
        activo["todos"] = "active"
        fondos = list(misfondos.find())

    fondo = fondos[0] if fondos else {}
    tag = fondo["tags"][0] if fondo and "tags" in fondo and fondo["tags"] else ""

    return render_template("index.html", fondos=fondos, activo=activo, fondo=fondo, tag=tag)

@app.route("/aportar", methods=["GET"])
def aportar():
    return render_template("aportar.html", mensaje="")

@app.route("/insertar", methods=["POST"])
def insertar():
    archivo = request.files["archivo"]
    titulo = request.form.get("titulo", "")
    descripcion = request.form.get("descripcion", "")
    tags = [t for t in TEMAS if request.form.get(t)]

    if archivo.filename == "":
        return render_template("aportar.html", mensaje="Hay que indicar un archivo de fondo.")
    
    if not archivo_permitido(archivo.filename):
        return render_template("aportar.html", mensaje="El archivo indicado no es una imagen!.")

    nombre_archivo = secure_filename(archivo.filename)
    ruta_guardado = os.path.join(app.config["UPLOAD_FOLDER"], nombre_archivo)
    archivo.save(ruta_guardado)

    nuevo_fondo = {
        "titulo": titulo,
        "descripcion": descripcion,
        "fondo": nombre_archivo,
        "tags": [t.upper() for t in tags]
    }

    misfondos.insert_one(nuevo_fondo)

    return render_template("aportar.html", mensaje="Fondo agregado correctamente.")


app.config['MAIL_SERVER'] = 'localhost'   
app.config['MAIL_PORT'] = 25
app.config['MAIL_USERNAME'] = ''           
app.config['MAIL_PASSWORD'] = ''           
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = False

mail = Mail(app)

@app.route("/form_email", methods=["GET"])
def form_email():
    _id = request.args.get("_id")
    if not _id:
        return "ID de fondo no proporcionado.", 400

    fondo_doc = misfondos.find_one({"_id": ObjectId(_id)})
    if not fondo_doc:
        return "Fondo no encontrado.", 404

    return render_template(
        "form_email.html",
        id=str(fondo_doc["_id"]),
        fondo=fondo_doc["fondo"],
        titulo=fondo_doc["titulo"],
        descripcion=fondo_doc["descripcion"]
    )


@app.route("/email", methods=["POST"])
def enviar_email():
    email_destino = request.form.get("email")
    _id = request.form.get("_id")

    if not email_destino or not _id:
        return "Faltan datos para enviar el email.", 400

    fondo_doc = misfondos.find_one({"_id": ObjectId(_id)})
    if not fondo_doc:
        return "Fondo no encontrado.", 404

    msg = Message(
        subject=f"Tu fondo de pantalla: {fondo_doc['titulo']}",
        sender="no-reply@localhost",
        recipients=[email_destino]
    )
    msg.html = render_template(
        "email.html",
        titulo=fondo_doc["titulo"],
        descripcion=fondo_doc["descripcion"]
    )

    ruta_imagen = os.path.join(app.config["UPLOAD_FOLDER"], fondo_doc["fondo"])
    with app.open_resource(ruta_imagen) as fp:
        msg.attach(fondo_doc["fondo"], "image/png", fp.read())

    mail.send(msg)

    return f"Email enviado correctamente a {email_destino}."

if __name__ == "__main__":
    app.run(debug=True)
