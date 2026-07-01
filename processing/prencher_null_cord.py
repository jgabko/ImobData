"""
Varre a tabela cep_coordenadas INTEIRA procurando linhas com latitude
e/ou longitude nulas, e tenta preenchê-las de novo a partir do CEP.

Diferente do geocode.py (que só cuida de CEPs novos, ausentes na tabela),
este script conserta CEPs que já existem em cep_coordenadas mas ficaram
sem coordenada numa rodada anterior (rede fora do ar, Nominatim
indisponível, endereço não encontrado, etc). É o script que você roda uma
vez para "curar" a tabela atual, e depois sempre que quiser tentar de novo
os CEPs que continuam sem coordenada.

Uso:
  python preencher_coordenadas_nulas.py
"""
import time

from persistence.supabase_f import fetch_ceps_coordenadas_nulas, salvar_cep_coordenadas
from processing.geocode.geocode_utils import resolver_cep


def main():
    pendentes = fetch_ceps_coordenadas_nulas()
    print(f"{len(pendentes)} CEPs com coordenadas nulas em cep_coordenadas.")

    resolvidos = 0
    for i, row in enumerate(pendentes, start=1):
        cep = row["cep"]
        endereco_conhecido = row.get("endereco")

        lat, lon, endereco, fonte = resolver_cep(cep, endereco_conhecido)
        salvar_cep_coordenadas(cep, lat, lon, endereco)

        if lat is not None and lon is not None:
            resolvidos += 1
            print(f"[{i}/{len(pendentes)}] {cep} -> ok via {fonte} ({lat:.5f}, {lon:.5f})")
        else:
            print(f"[{i}/{len(pendentes)}] {cep} -> continua sem coordenada (endereço: {endereco!r})")

        time.sleep(0.3)

    print(f"\nConcluído. {resolvidos}/{len(pendentes)} CEPs corrigidos nesta rodada.")


if __name__ == "__main__":
    main()