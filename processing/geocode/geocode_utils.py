"""
Lógica de geocodificação de CEPs, compartilhada entre geocode.py e
preencher_coordenadas_nulas.py.

Estratégia (nessa ordem, parando na primeira que funcionar):
  1) BrasilAPI  -> agrega Correios/ViaCEP/Widenet e, para boa parte dos CEPs
     urbanos, já devolve latitude/longitude prontas.
  2) Endereço conhecido (se já tivermos) ou ViaCEP + Nominatim/OpenStreetMap
     -> usado só quando a BrasilAPI não tem coordenada para aquele CEP.
     Respeita o limite de 1 requisição/segundo do Nominatim.

Importante: todas as comparações usam `is not None` em vez de checagem de
"verdadeiro" (`if lat and lon`), porque latitude/longitude no Brasil são
sempre números negativos e não-zero, mas depender de truthiness é frágil
e engana o próximo dev que mexer nisso.
"""
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

LOCATIONIQ_API_KEY = os.environ.get("LOCATIONIQ_API_KEY")
HEADERS_NOMINATIM = {
    "User-Agent": "ImobTestes-Curitiba/1.0 (contato@example.com)"
}


def _normalizar_cep(cep: str) -> str:
    return "".join(filter(str.isdigit, str(cep))).zfill(8)


def buscar_coordenadas_brasilapi(cep: str):
    """Retorna (lat, lon, endereco). lat/lon podem vir None se a fonte não
    tiver coordenada para esse CEP, mesmo que o endereço exista."""
    cep = _normalizar_cep(cep)
    try:
        r = requests.get(f"https://brasilapi.com.br/api/cep/v2/{cep}", timeout=10)
        if r.status_code != 200:
            print(f"  [BrasilAPI] status HTTP {r.status_code}")
            return None, None, None
        dados = r.json()
        endereco = ", ".join(filter(None, [
            dados.get("street"), dados.get("neighborhood"), dados.get("city"), dados.get("state"),
        ])) or None
        coords = (dados.get("location") or {}).get("coordinates") or {}
        lat, lon = coords.get("latitude"), coords.get("longitude")
        if lat is not None and lon is not None:
            return float(lat), float(lon), endereco
        return None, None, endereco
    except requests.RequestException as e:
        print(f"  [BrasilAPI] erro de rede: {e}")
        return None, None, None
    except (ValueError, KeyError, TypeError) as e:
        print(f"  [BrasilAPI] erro ao processar resposta: {e}")
        return None, None, None


def buscar_endereco_viacep(cep: str):
    cep = _normalizar_cep(cep)
    try:
        r = requests.get(f"https://viacep.com.br/ws/{cep}/json/", timeout=10)
        if r.status_code != 200:
            print(f"  [ViaCEP] status HTTP {r.status_code}")
            return None
        dados = r.json()
        if dados.get("erro"):
            return None
        partes = [dados.get("logradouro"), dados.get("bairro"), dados.get("localidade"), dados.get("uf")]
        return ", ".join(p for p in partes if p) or None
    except requests.RequestException as e:
        print(f"  [ViaCEP] erro de rede: {e}")
        return None
    except ValueError as e:
        print(f"  [ViaCEP] resposta não é JSON válido: {e}")
        return None


def geocodificar_nominatim(endereco: str):
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": f"{endereco}, Brasil", "format": "json", "limit": 1},
            headers=HEADERS_NOMINATIM,
            timeout=10,
        )
        if r.status_code != 200:
            print(f"  [Nominatim] status HTTP {r.status_code}: {r.text[:150]!r}")
            return None, None
        resultados = r.json()
        if not resultados:
            return None, None
        return float(resultados[0]["lat"]), float(resultados[0]["lon"])
    except requests.RequestException as e:
        print(f"  [Nominatim] erro de rede: {e}")
        return None, None
    except (ValueError, KeyError, IndexError) as e:
        print(f"  [Nominatim] erro ao processar resposta: {e}")
        return None, None


def geocodificar_photon(endereco: str):
    """Fallback via Photon (photon.komoot.io), API pública sobre dados do
    OpenStreetMap. Não exige chave e, ao contrário do servidor de demo do
    Nominatim, não bloqueia com 403 uso automatizado/em lote vindo de
    servidores e nuvens (esse é o bloqueio que a policy da OSM Foundation
    aplica: https://operations.osmfoundation.org/policies/nominatim/)."""
    try:
        r = requests.get(
            "https://photon.komoot.io/api/",
            params={"q": f"{endereco}, Brasil", "limit": 1, "lang": "pt"},
            timeout=10,
        )
        if r.status_code != 200:
            print(f"  [Photon] status HTTP {r.status_code}: {r.text[:150]!r}")
            return None, None
        dados = r.json()
        features = dados.get("features") or []
        if not features:
            return None, None
        lon, lat = features[0]["geometry"]["coordinates"]
        return float(lat), float(lon)
    except requests.RequestException as e:
        print(f"  [Photon] erro de rede: {e}")
        return None, None
    except (ValueError, KeyError, IndexError, TypeError) as e:
        print(f"  [Photon] erro ao processar resposta: {e}")
        return None, None


def geocodificar_locationiq(endereco: str):
    """Fallback via LocationIQ. Autenticado por API key (LOCATIONIQ_API_KEY
    no .env) em vez de depender da reputação do IP — diferente dos
    servidores públicos do Nominatim e do Photon, que bloqueiam com 403
    quando o IP de origem está em alguma blocklist de abuso deles.
    Plano grátis: https://locationiq.com/register (5.000 req/dia).
    Retorna (None, None) se LOCATIONIQ_API_KEY não estiver configurada,
    para cair automaticamente nos próximos fallbacks."""
    if not LOCATIONIQ_API_KEY:
        return None, None
    try:
        r = requests.get(
            "https://us1.locationiq.com/v1/search",
            params={
                "key": LOCATIONIQ_API_KEY,
                "q": f"{endereco}, Brasil",
                "format": "json",
                "limit": 1,
                "countrycodes": "br",
            },
            timeout=10,
        )
        if r.status_code != 200:
            print(f"  [LocationIQ] status HTTP {r.status_code}: {r.text[:150]!r}")
            return None, None
        resultados = r.json()
        if not resultados:
            return None, None
        return float(resultados[0]["lat"]), float(resultados[0]["lon"])
    except requests.RequestException as e:
        print(f"  [LocationIQ] erro de rede: {e}")
        return None, None
    except (ValueError, KeyError, IndexError, TypeError) as e:
        print(f"  [LocationIQ] erro ao processar resposta: {e}")
        return None, None


def resolver_cep(cep: str, endereco_conhecido: str | None = None):
    """Retorna (lat, lon, endereco, fonte).

    `endereco_conhecido`: se já tivermos um endereço salvo (ex: de uma
    tentativa anterior que achou o endereço mas não a coordenada), pulamos
    a chamada ao ViaCEP e vamos direto pra geocodificação com ele.

    Ordem de fallback pra geocodificação a partir do endereço: LocationIQ
    primeiro (autenticado por chave, não sofre bloqueio de IP), depois
    Photon e por último Nominatim, caso algum dia voltem a aceitar as
    requisições vindas do seu IP.
    """
    lat, lon, endereco = buscar_coordenadas_brasilapi(cep)
    if lat is not None and lon is not None:
        return lat, lon, endereco, "BrasilAPI"

    endereco = endereco or endereco_conhecido or buscar_endereco_viacep(cep)
    if endereco:
        lat, lon = geocodificar_locationiq(endereco)
        if lat is not None and lon is not None:
            return lat, lon, endereco, "LocationIQ"

        time.sleep(1.0)
        lat, lon = geocodificar_photon(endereco)
        if lat is not None and lon is not None:
            return lat, lon, endereco, "Photon"

        time.sleep(1.1)  # respeita o limite de 1 req/s do Nominatim
        lat, lon = geocodificar_nominatim(endereco)
        if lat is not None and lon is not None:
            return lat, lon, endereco, "Nominatim"

    return None, None, endereco, None