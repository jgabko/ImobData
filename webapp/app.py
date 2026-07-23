"""
ImobData Web — frontend novo (Flask + HTML/CSS/JS puro), lendo o MESMO
banco SQLite (imobdata.db) usado pelo dashboard.py em Streamlit.

Este arquivo NÃO altera nada do fluxo existente (pipeline, streamlit,
persistence/*). Ele apenas abre suas próprias conexões de leitura ao
mesmo arquivo .db, reaproveitando o schema definido em persistence/db.py.

Rodar com:
    python webapp/app.py
ou:
    flask --app webapp.app run --debug

Depois acesse http://127.0.0.1:5000
"""
import json
import sqlite3
from pathlib import Path

from flask import Flask, jsonify, render_template, request

# Reaproveita o caminho do banco já definido em persistence/db.py, sem
# importar nada que dispare efeitos colaterais além de abrir/ler.
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "imobdata.db"

try:
    with open(BASE_DIR / "metricas_modelo.json", "r", encoding="utf-8") as f:
        MARGEM_ERRO = json.load(f).get("margem_erro", 90_000)
except FileNotFoundError:
    MARGEM_ERRO = 90_000

STATUS_VALIDOS = {
    "acima": "Acima do mercado",
    "abaixo": "Abaixo do mercado",
    "dentro": "Dentro da faixa esperada",
}

app = Flask(__name__)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def parse_json_list(raw):
    if not raw:
        return []
    try:
        val = json.loads(raw)
        return val if isinstance(val, list) else [val]
    except (TypeError, ValueError):
        return [raw]


def row_to_imovel(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["caracteristicas_imovel"] = parse_json_list(d.get("caracteristicas_imovel"))
    d["caracteristicas_condominio"] = parse_json_list(d.get("caracteristicas_condominio"))
    return d


# ----------------------------------------------------------------------
# Query base compartilhada: imoveis_raw + precos_previstos (+ cep_coordenadas)
# ----------------------------------------------------------------------
BASE_SELECT = """
    SELECT
        r.id, r.url, r.titulo, r.descricao,
        r.preco, r.condominio, r.iptu,
        r.bairro, r.cidade, r.estado, r.cep,
        r.metragem, r.quartos, r.banheiros, r.vagas,
        r.caracteristicas_imovel, r.caracteristicas_condominio,
        p.preco_real, p.preco_previsto, p.diferenca, p.status, p.criado_em,
        c.latitude, c.longitude
    FROM imoveis_raw r
    JOIN precos_previstos p ON p.imovel_id = r.id
    LEFT JOIN cep_coordenadas c ON c.cep = r.cep
"""


def montar_filtros(args):
    """Constrói cláusula WHERE + params a partir da query string."""
    clauses = []
    params = []

    bairro = args.get("bairro")
    if bairro:
        clauses.append("r.bairro = ?")
        params.append(bairro)

    q = args.get("q", "").strip()
    if q:
        clauses.append("(r.titulo LIKE ? OR r.bairro LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%"])

    status_key = args.get("status")
    if status_key in STATUS_VALIDOS:
        clauses.append("p.status = ?")
        params.append(STATUS_VALIDOS[status_key])

    preco_min = args.get("preco_min", type=float)
    if preco_min is not None:
        clauses.append("p.preco_real >= ?")
        params.append(preco_min)

    preco_max = args.get("preco_max", type=float)
    if preco_max is not None:
        clauses.append("p.preco_real <= ?")
        params.append(preco_max)

    quartos_min = args.get("quartos_min", type=int)
    if quartos_min is not None:
        clauses.append("r.quartos >= ?")
        params.append(quartos_min)

    banheiros_min = args.get("banheiros_min", type=int)
    if banheiros_min is not None:
        clauses.append("r.banheiros >= ?")
        params.append(banheiros_min)

    vagas_min = args.get("vagas_min", type=int)
    if vagas_min is not None:
        clauses.append("r.vagas >= ?")
        params.append(vagas_min)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where, params


COLUNAS_ORDENACAO = {
    "preco": "p.preco_real",
    "preco_previsto": "p.preco_previsto",
    "diferenca": "p.diferenca",
    "metragem": "r.metragem",
    "quartos": "r.quartos",
    "bairro": "r.bairro",
    "criado_em": "p.criado_em",
}


# ----------------------------------------------------------------------
# Páginas
# ----------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html", margem_erro=MARGEM_ERRO)


# ----------------------------------------------------------------------
# API
# ----------------------------------------------------------------------
@app.route("/api/stats")
def api_stats():
    conn = get_conn()
    try:
        cur = conn.execute(
            f"SELECT p.status, r.bairro, p.preco_real FROM imoveis_raw r "
            f"JOIN precos_previstos p ON p.imovel_id = r.id"
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    total = len(rows)
    contagem = {"acima": 0, "abaixo": 0, "dentro": 0}
    mapa_reverso = {v: k for k, v in STATUS_VALIDOS.items()}
    bairros = set()
    soma_preco = 0.0
    for r in rows:
        chave = mapa_reverso.get(r["status"])
        if chave:
            contagem[chave] += 1
        if r["bairro"]:
            bairros.add(r["bairro"])
        soma_preco += r["preco_real"] or 0

    return jsonify(
        {
            "total": total,
            "bairros": len(bairros),
            "acima_do_mercado": contagem["acima"],
            "abaixo_do_mercado": contagem["abaixo"],
            "dentro_da_faixa": contagem["dentro"],
            "preco_medio": (soma_preco / total) if total else 0,
            "margem_erro": MARGEM_ERRO,
        }
    )


@app.route("/api/imoveis")
def api_imoveis():
    where, params = montar_filtros(request.args)

    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 20, type=int), 1), 100)
    offset = (page - 1) * per_page

    sort_by = COLUNAS_ORDENACAO.get(request.args.get("sort_by"), "p.criado_em")
    sort_dir = "ASC" if request.args.get("sort_dir") == "asc" else "DESC"

    conn = get_conn()
    try:
        total = conn.execute(
            f"SELECT COUNT(*) AS c FROM imoveis_raw r "
            f"JOIN precos_previstos p ON p.imovel_id = r.id "
            f"LEFT JOIN cep_coordenadas c ON c.cep = r.cep {where}",
            params,
        ).fetchone()["c"]

        rows = conn.execute(
            f"{BASE_SELECT} {where} ORDER BY {sort_by} {sort_dir} LIMIT ? OFFSET ?",
            [*params, per_page, offset],
        ).fetchall()
    finally:
        conn.close()

    return jsonify(
        {
            "items": [row_to_imovel(r) for r in rows],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": max((total + per_page - 1) // per_page, 1),
        }
    )


@app.route("/api/imoveis/<int:imovel_id>")
def api_imovel_detalhe(imovel_id):
    conn = get_conn()
    try:
        row = conn.execute(f"{BASE_SELECT} WHERE r.id = ?", [imovel_id]).fetchone()
    finally:
        conn.close()

    if row is None:
        return jsonify({"erro": "Imóvel não encontrado"}), 404
    return jsonify(row_to_imovel(row))


@app.route("/api/bairros")
def api_bairros():
    conn = get_conn()
    try:
        rows = conn.execute(
            """
            SELECT
                r.bairro AS bairro,
                COUNT(*) AS total,
                AVG(p.preco_real) AS preco_medio,
                AVG(p.diferenca) AS diferenca_media,
                SUM(CASE WHEN p.status = 'Acima do mercado' THEN 1 ELSE 0 END) AS acima,
                SUM(CASE WHEN p.status = 'Abaixo do mercado' THEN 1 ELSE 0 END) AS abaixo,
                SUM(CASE WHEN p.status = 'Dentro da faixa esperada' THEN 1 ELSE 0 END) AS dentro
            FROM imoveis_raw r
            JOIN precos_previstos p ON p.imovel_id = r.id
            WHERE r.bairro IS NOT NULL AND r.bairro != ''
            GROUP BY r.bairro
            ORDER BY total DESC
            """
        ).fetchall()
    finally:
        conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/mapa")
def api_mapa():
    where, params = montar_filtros(request.args)
    conn = get_conn()
    try:
        rows = conn.execute(
            f"""
            SELECT r.id, r.titulo, r.bairro, r.url,
                   p.preco_real, p.preco_previsto, p.status,
                   c.latitude, c.longitude
            FROM imoveis_raw r
            JOIN precos_previstos p ON p.imovel_id = r.id
            LEFT JOIN cep_coordenadas c ON c.cep = r.cep
            {where}
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    pontos = [dict(r) for r in rows if r["latitude"] is not None and r["longitude"] is not None]
    sem_coordenadas = len(rows) - len(pontos)
    return jsonify({"pontos": pontos, "sem_coordenadas": sem_coordenadas})


@app.route("/api/distribuicao")
def api_distribuicao():
    """Valores de diferença (real - previsto) + status, para o histograma."""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT diferenca, status FROM precos_previstos WHERE diferenca IS NOT NULL"
        ).fetchall()
    finally:
        conn.close()
    return jsonify([dict(r) for r in rows])


if __name__ == "__main__":
    app.run(debug=True)