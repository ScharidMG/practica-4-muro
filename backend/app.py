# API del murazo de mensajes: listar y publicar, guardando en Firestore. 
import os, uuid
from flask import Flask, request, jsonify
from google.cloud import firestore
from google.api_core.exceptions import NotFound

app = Flask(__name__)
db = firestore.Client(database=os.environ.get("BASE_DATOS", "(default)"))
INSTANCIA = uuid.uuid4().hex[:6]


@app.after_request
def permitir_navegador(respuesta):
    respuesta.headers["Access-Control-Allow-Origin"] = os.environ.get("ORIGEN_PERMITIDO", "*")
    respuesta.headers["Access-Control-Allow-Headers"] = "Content-Type"
    respuesta.headers["Access-Control-Allow-Methods"] = "GET, POST"
    return respuesta


@app.get("/")
def salud():
    return "ok"


@app.get("/mensajes")
def listar():
    consulta = (db.collection("mensajes")
                  .order_by("creado", direction=firestore.Query.DESCENDING)
                  .limit(20))
    mensajes = []
    for d in consulta.stream():
        campos = d.to_dict()
        mensajes.append({
            "id": d.id,
            "autor": campos.get("autor"),
            "texto": campos.get("texto"),
            "likes": campos.get("likes", 0),   # los mensajes viejos no tienen el campo
        })
    return jsonify(instancia=INSTANCIA, mensajes=mensajes)


@app.post("/mensajes")
def crear():
    datos = request.get_json(silent=True) or {}
    autor = str(datos.get("autor", "")).strip()[:40]
    texto = str(datos.get("texto", "")).strip()[:280]
    if not autor or not texto:
        return jsonify(error="faltan autor o texto"), 400
    db.collection("mensajes").add({
        "autor": autor,
        "texto": texto,
        "creado": firestore.SERVER_TIMESTAMP,
        "likes": 0,
    })
    return jsonify(ok=True, instancia=INSTANCIA), 201


@app.post("/mensajes/<id_mensaje>/like")
def dar_like(id_mensaje):
    documento = db.collection("mensajes").document(id_mensaje)
    try:
        # Increment suma en el servidor: no hay que leer antes y no se pierden votos simultaneos
        documento.update({"likes": firestore.Increment(1)})
    except NotFound:
        return jsonify(error="ese mensaje no existe"), 404
    return jsonify(ok=True, instancia=INSTANCIA)
