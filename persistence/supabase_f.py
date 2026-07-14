"""
Camada de acesso a dados usada pelo pipeline de precificação, pelo
geocode_cep.py e pelo dashboard.

Antes usava Supabase; agora usa SQLite local (persistence/db.py).
As assinaturas de todas as funções foram mantidas iguais, então
dashboard.py, pipeline.py, geocode.py etc. não precisam mudar nada.

Tabelas (ver schema completo em persistence/db.py):
  imoveis_raw
    id (pk autoincrement), url (unique), preco, condominio, iptu, bairro,
    cidade, estado, cep, metragem, quartos, banheiros, vagas,
    caracteristicas_imovel (text/json), caracteristicas_condominio (text/json),
    checked (bool, default 0)
  precos_previstos
    imovel_id (fk -> imoveis_raw.id, pk),
    preco_real, preco_previsto, diferenca, status, criado_em (default now)
  cep_coordenadas
    cep (pk), latitude, longitude, endereco
"""
import pandas as pd

from persistence.db import get_connection, db_cursor, rows_to_dicts, init_db

# Garante que as tabelas existem assim que este módulo é importado
init_db()


# ----------------------------------------------------------------------
# Imóveis / precificação
# ----------------------------------------------------------------------
def fetch_imoveis_pendentes() -> list:
    """Imóveis que já têm preço real (raspado da OLX) mas ainda não tiveram
    o preço de mercado previsto/comparado (checked = 0)."""
    print("[DB] Buscando imóveis pendentes de precificação...")
    try:
        with db_cursor() as (conn, cur):
            cur.execute("SELECT * FROM imoveis_raw WHERE checked = 0")
            dados = rows_to_dicts(cur.fetchall())
        print(f"[DB] {len(dados)} imóveis encontrados.")
        return dados
    except Exception as e:
        print(f"[DB] Erro ao buscar imóveis pendentes: {e}")
        return []


def salvar_comparacao_preco(imovel_id, preco_real, preco_previsto, diferenca, status):
    """Salva a comparação (preço real x previsto) e marca o imóvel como
    processado (checked = 1)."""
    try:
        preco_real = float(round(float(preco_real), 2))
        preco_previsto = int(round(float(preco_previsto)))
        diferenca = float(round(float(diferenca), 2))

        with db_cursor() as (conn, cur):
            cur.execute(
                """
                INSERT INTO precos_previstos
                    (imovel_id, preco_real, preco_previsto, diferenca, status, criado_em)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(imovel_id) DO UPDATE SET
                    preco_real = excluded.preco_real,
                    preco_previsto = excluded.preco_previsto,
                    diferenca = excluded.diferenca,
                    status = excluded.status,
                    criado_em = CURRENT_TIMESTAMP
                """,
                (imovel_id, preco_real, preco_previsto, diferenca, status),
            )
            cur.execute(
                "UPDATE imoveis_raw SET checked = 1 WHERE id = ?", (imovel_id,)
            )
        print(f"[DB] OK: imóvel {imovel_id} -> previsto R$ {preco_previsto:,} ({status})")
    except Exception as e:
        print(f"[DB] Erro ao salvar comparação do imóvel {imovel_id}: {e}")


# ----------------------------------------------------------------------
# Geocodificação de CEPs
# ----------------------------------------------------------------------
def fetch_ceps_unicos() -> list:
    """Todos os CEPs distintos presentes em imoveis_raw."""
    try:
        with db_cursor() as (conn, cur):
            cur.execute(
                "SELECT DISTINCT cep FROM imoveis_raw WHERE cep IS NOT NULL AND cep != ''"
            )
            return sorted(row["cep"] for row in cur.fetchall())
    except Exception as e:
        print(f"[DB] Erro ao buscar CEPs: {e}")
        return []


def fetch_ceps_ja_geocodificados() -> set:
    try:
        with db_cursor() as (conn, cur):
            cur.execute("SELECT cep FROM cep_coordenadas")
            return {row["cep"] for row in cur.fetchall()}
    except Exception as e:
        print(f"[DB] Erro ao buscar CEPs já geocodificados: {e}")
        return set()


def salvar_cep_coordenadas(cep, latitude, longitude, endereco):
    try:
        with db_cursor() as (conn, cur):
            cur.execute(
                """
                INSERT INTO cep_coordenadas (cep, latitude, longitude, endereco)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(cep) DO UPDATE SET
                    latitude = excluded.latitude,
                    longitude = excluded.longitude,
                    endereco = excluded.endereco
                """,
                (cep, latitude, longitude, endereco),
            )
    except Exception as e:
        print(f"[DB] Erro ao salvar coordenadas do CEP {cep}: {e}")


def fetch_ceps_com_coordenadas_ok() -> set:
    """CEPs que já têm latitude E longitude preenchidas em cep_coordenadas."""
    try:
        with db_cursor() as (conn, cur):
            cur.execute(
                """
                SELECT cep FROM cep_coordenadas
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                """
            )
            return {row["cep"] for row in cur.fetchall()}
    except Exception as e:
        print(f"[DB] Erro ao buscar CEPs com coordenadas OK: {e}")
        return set()


def fetch_ceps_coordenadas_nulas() -> list:
    """Linhas de cep_coordenadas com latitude OU longitude nulas —
    candidatas a serem re-geocodificadas."""
    try:
        with db_cursor() as (conn, cur):
            cur.execute(
                """
                SELECT cep, endereco FROM cep_coordenadas
                WHERE latitude IS NULL OR longitude IS NULL
                """
            )
            return rows_to_dicts(cur.fetchall())
    except Exception as e:
        print(f"[DB] Erro ao buscar CEPs com coordenadas nulas: {e}")
        return []


# ----------------------------------------------------------------------
# Dados consolidados para o dashboard
# ----------------------------------------------------------------------
def fetch_dados_dashboard() -> pd.DataFrame:
    """Junta imoveis_raw + precos_previstos + cep_coordenadas em um único
    DataFrame, pronto para os gráficos e o mapa do dashboard."""
    conn = get_connection()
    try:
        imoveis = pd.read_sql_query("SELECT * FROM imoveis_raw", conn)
        previstos = pd.read_sql_query("SELECT * FROM precos_previstos", conn)
        coords = pd.read_sql_query("SELECT * FROM cep_coordenadas", conn)
    finally:
        conn.close()

    if imoveis.empty or previstos.empty:
        return pd.DataFrame()

    df = imoveis.merge(
        previstos, left_on="id", right_on="imovel_id", how="inner", suffixes=("", "_prev")
    )
    if not coords.empty:
        df = df.merge(coords, on="cep", how="left")
    return df