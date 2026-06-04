import requests
from typing import List, Optional
from urllib.parse import urljoin
import html5lib
from bs4 import BeautifulSoup, Tag
import json
import time




headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
}

def olx_listagens():
    url="https://www.olx.com.br/imoveis/venda/estado-pr/curitiba"

    max_pages=10

    for page in range(1,max_pages+1):
        url_atual = f"{url}?o={page}"

        response=requests.get(url_atual,headers=headers)

        soup = BeautifulSoup(response.content, "html5lib")

        next_data_script = soup.find("script", id="__NEXT_DATA__")



        if next_data_script:
                try:
                    # Load the text inside the script tag as a JSON dictionary
                    data = json.loads(next_data_script.string)
                    
                    #Estudar essa linha
                    #Estudar .get() para JSON
                    ads = data.get("props", {}).get("pageProps", {}).get("ads", [])
                    
                    imoveis_extraidos = []

                    for ad in ads:
                        title = ad.get("subject")
                        
                        if title:
                            preco = ad.get("priceValue", "Preço não informado")
                            
                            # 1. Criamos variáveis vazias para garantir que não dê erro se o anúncio não tiver essa info
                            tamanho = "N/A"
                            quartos = "N/A"
                            banheiros = "N/A"
                            vagas = "N/A"
                            
                            # 2. Entramos na "sub-gaveta" properties do anúncio atual
                            propriedades = ad.get("properties", [])
                            
                            # 3. Lemos ficha por ficha procurando os números
                            for prop in propriedades:
                                nome_da_propriedade = prop.get("name")
                                valor = prop.get("value")
                                
                                if nome_da_propriedade == "size":
                                    tamanho = valor
                                elif nome_da_propriedade == "rooms":
                                    quartos = valor
                                elif nome_da_propriedade == "bathrooms":
                                    banheiros = valor
                                elif nome_da_propriedade == "garage_spaces":
                                    vagas = valor
                            
                            # 4. Salvamos tudo organizado
                            imovel = {
                                "Titulo": title,
                                "Preco": preco,
                                "Tamanho": tamanho,
                                "Quartos": quartos,
                                "Banheiros": banheiros,
                                "Vagas": vagas
                            }
                            
                            imoveis_extraidos.append(imovel)


                except Exception as e:
                    print(f"Error parsing data on page: {e}")
        else:
            print(f"Could not find the data block on page. They might be blocking the request.")
            
            
            time.sleep(2)

        for item in imoveis_extraidos:
            print(f"🏠 {item['Titulo']} | 💰 {item['Preco']}")
            print(f"📏 {item['Tamanho']} | 🛏️ {item['Quartos']} quartos | 🚿 {item['Banheiros']} banheiros | 🚗 {item['Vagas']} vagas")
            print("-" * 60)


def olx_url_ad(url: str):
    
