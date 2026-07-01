"""
Geocodifica os CEPs de imoveis_raw que ainda não têm coordenadas em
cep_coordenadas, e salva o resultado direto no Supabase.

CORREÇÃO em relação à versão anterior:
  O antigo `fetch_ceps_ja_geocodificados()` considerava "resolvido" qualquer
  CEP que já tivesse uma LINHA na tabela cep_coordenadas — mesmo que
  latitude/longitude estivessem nulas (o que acontece quando a
  geocodificação falha, mas salvamos a linha do mesmo jeito para não
  perder o endereço já descoberto). Resultado: um CEP que falhava uma vez
  ficava "resolvido" para sempre e nunca mais era tentado de novo — foi
  por isso que a tabela inteira acabou com coordenadas vazias.

  Agora usamos `fetch_ceps_com_coordenadas_ok()`, que só considera
  resolvido quem realmente tem latitude E longitude preenchidas. CEPs que
  já existem na tabela mas com coordenada nula continuam sendo pulados
  aqui (esse é o trabalho do preencher_coordenadas_nulas.py) — este script
  cuida só de CEPs 100% novos.

Uso:
  python geocode.py
"""
import time

from persistence.supabase_f import fetch_ceps_com_coordenadas_ok, fetch_ceps_unicos, salvar_cep_coordenadas
from processing.geocode.geocode_utils import resolver_cep


def main():
    ceps_unicos = fetch_ceps_unicos()
    ja_resolvidos = fetch_ceps_com_coordenadas_ok()
    pendentes = [c for c in ceps_unicos if c not in ja_resolvidos]

    print(f"{len(ceps_unicos)} CEPs únicos no total, {len(pendentes)} ainda sem coordenadas.")

    encontrados = 0
    for i, cep in enumerate(pendentes, start=1):
        lat, lon, endereco, fonte = resolver_cep(cep)
        salvar_cep_coordenadas(cep, lat, lon, endereco)

        if lat is not None and lon is not None:
            encontrados += 1
            print(f"[{i}/{len(pendentes)}] {cep} -> ok via {fonte} ({lat:.5f}, {lon:.5f})")
        else:
            print(f"[{i}/{len(pendentes)}] {cep} -> não encontrado (endereço: {endereco!r})")

        time.sleep(0.3)  # respiro entre CEPs mesmo quando só BrasilAPI foi usada

    print(f"\nConcluído. {encontrados}/{len(pendentes)} CEPs novos resolvidos com sucesso.")


if __name__ == "__main__":
    main()