"""
Conexão e schema do banco SQLite local (substitui o Supabase).

Um único arquivo .db na raiz do projeto (ImobData/imobdata.db) guarda tudo.
Nenhuma credencial, nenhuma rede, nenhum "projeto pausado" — o banco é
apenas um arquivo local.
"""
import sqlite3
from pathlib import Path
from contextlib import contextmanager

# imobdata.db vai ficar na raiz do projeto (um nível acima de persistence/)
DB_PATH = Path(__file__).resolve().parent.parent / "imobdata.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS imoveis_raw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE,
    preco REAL,
    condominio REAL,
    iptu REAL,
    bairro TEXT,
    cidade TEXT,
    estado TEXT,
    cep TEXT,
    metragem REAL,
    quartos INTEGER,
    banheiros INTEGER,
    vagas INTEGER,
    caracteristicas_imovel TEXT,
    caracteristicas_condominio TEXT,
    checked BOOLEAN DEFAULT 0
);

CREATE TABLE IF NOT EXISTS precos_previstos (
    imovel_id INTEGER PRIMARY KEY REFERENCES imoveis_raw(id),
    preco_real REAL,
    preco_previsto REAL,
    diferenca REAL,
    status TEXT,
    criado_em TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cep_coordenadas (
    cep TEXT PRIMARY KEY,
    latitude REAL,
    longitude REAL,
    endereco TEXT
);
"""


def get_connection() -> sqlite3.Connection:
    """Abre uma conexão nova. row_factory faz as linhas se comportarem
    como dicts (row['coluna']), igual ao formato que o supabase-py retornava."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Cria as tabelas se ainda não existirem. Chame uma vez ao iniciar
    o projeto (ou deixe supabase_f.py chamar automaticamente no import)."""
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def db_cursor():
    """Context manager: abre conexão, entrega (conn, cursor), faz commit
    no final ou rollback se der erro, e sempre fecha a conexão."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield conn, cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def rows_to_dicts(rows) -> list[dict]:
    """Converte sqlite3.Row -> dict, igual ao formato .data do supabase-py."""
    return [dict(r) for r in rows]