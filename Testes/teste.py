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

url="https://pr.olx.com.br/regiao-de-curitiba-e-paranagua/imoveis/casa-a-venda-em-condominio-fechado-com-04-suites-ao-lado-do-parque-tingui-em-curitiba-pr-1346802185?lis=listing_1001"

response=requests.get(url,headers=headers)

soup = BeautifulSoup(response.content, "html5lib")

next_data_script = soup.find("script", id="__NEXT_DATA__")

#print(next_data_script)

#data = json.loads(next_data_script.string)

#localizacao = data.get('location')

print(soup)

