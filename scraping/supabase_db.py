"""
Camada de gravação usada pelo scraper (olx_async.py) para salvar imóveis
raspados. Antes usava Supabase; agora grava direto no SQLite local.

Mantém os mesmos nomes de função (get_supabase_client / salvar_no_supabase)
por compatibilidade, mesmo não havendo mais "cliente" de fato — só que
get_supabase_client agora retorna a conexão sqlite3.
"""
import json
import sqlite3

from persistence.db import get_connection, init_db


def _serializar_valor(v):
    """SQLite só aceita tipos primitivos (str, int, float, bytes, None).
    Campos como listas (ex: caracteristicas_imovel: List[str]) ou dicts
    precisam virar uma string JSON antes de serem gravados."""
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)
    return v

# Garante que as tabelas existem assim que este módulo é importado
init_db()


def get_supabase_client() -> sqlite3.Connection:
    """Mantido por compatibilidade com o código antigo. Retorna uma conexão
    sqlite3 em vez de um cliente Supabase."""
    return get_connection()


def _garantir_colunas(conn, nome_tabela: str, colunas_necessarias: list[str]):
    """Adiciona automaticamente qualquer coluna que apareça nos dados
    raspados mas ainda não exista na tabela local. Isso evita que o
    scraper quebre sempre que o schema do site (e portanto do
    ImovelCuritibaSchema) ganhar um campo novo."""
    cur = conn.execute(f"PRAGMA table_info({nome_tabela})")
    colunas_existentes = {row[1] for row in cur.fetchall()}  # row[1] = nome da coluna

    for coluna in colunas_necessarias:
        if coluna not in colunas_existentes:
            print(f"[BANCO DE DADOS] Coluna '{coluna}' não existe em '{nome_tabela}' — criando (tipo TEXT).")
            conn.execute(f"ALTER TABLE {nome_tabela} ADD COLUMN {coluna} TEXT")
    conn.commit()


def salvar_no_supabase(dados: list[dict], nome_tabela: str = "imoveis_raw"):
    """
    Recebe uma lista de dicionários e realiza um INSERT OR IGNORE na tabela
    local. Registros cuja 'url' já exista são simplesmente ignorados
    (mesmo comportamento do upsert com ignore_duplicates=True que era usado
    no Supabase).
    """
    if not dados:
        print("Aviso: Nenhum dado disponível para salvar.")
        return None

    conn = get_connection()
    try:
        print(f"\n[BANCO DE DADOS] Tentando inserir {len(dados)} imóveis na tabela '{nome_tabela}'...")

        # Colunas dinâmicas: junta as chaves de TODOS os dicts (não só o
        # primeiro), já que registros diferentes podem ter campos opcionais
        # ausentes em uns e presentes em outros.
        colunas = sorted({chave for registro in dados for chave in registro.keys()})

        # Garante que a tabela tenha todas essas colunas antes de inserir
        _garantir_colunas(conn, nome_tabela, colunas)
        placeholders = ", ".join("?" for _ in colunas)
        colunas_sql = ", ".join(colunas)

        query = (
            f"INSERT OR IGNORE INTO {nome_tabela} ({colunas_sql}) "
            f"VALUES ({placeholders})"
        )

        valores = [tuple(_serializar_valor(d.get(c)) for c in colunas) for d in dados]

        cur = conn.cursor()
        cur.executemany(query, valores)
        conn.commit()

        inseridos = cur.rowcount if cur.rowcount is not None else 0
        print(
            f"✅ Processamento concluído! {inseridos} registro(s) novo(s) salvo(s). "
            f"(Duplicatas por 'url' ignoradas)."
        )
        return valores
    except Exception as e:
        conn.rollback()
        print(f"❌ Erro ao inserir dados no banco local: {e}")
        return None
    finally:
        conn.close()