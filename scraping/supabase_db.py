"""
Camada de gravação usada pelo scraper (olx_async.py) para salvar imóveis
raspados. Antes usava Supabase; agora grava direto no SQLite local.

Mantém os mesmos nomes de função (get_supabase_client / salvar_no_supabase)
por compatibilidade, mesmo não havendo mais "cliente" de fato — só que
get_supabase_client agora retorna a conexão sqlite3.
"""
import sqlite3

from persistence.db import get_connection, init_db

# Garante que as tabelas existem assim que este módulo é importado
init_db()


def get_supabase_client() -> sqlite3.Connection:
    """Mantido por compatibilidade com o código antigo. Retorna uma conexão
    sqlite3 em vez de um cliente Supabase."""
    return get_connection()


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

        # Colunas dinâmicas: usa as chaves do primeiro dict como referência.
        # Assume que todos os dicts da lista têm o mesmo formato de chaves
        # (mesmo comportamento implícito que o upsert em lote do Supabase).
        colunas = list(dados[0].keys())
        placeholders = ", ".join("?" for _ in colunas)
        colunas_sql = ", ".join(colunas)

        query = (
            f"INSERT OR IGNORE INTO {nome_tabela} ({colunas_sql}) "
            f"VALUES ({placeholders})"
        )

        valores = [tuple(d.get(c) for c in colunas) for d in dados]

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