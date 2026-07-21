<div align="center">

  <h1>ImobData</h1>

  <p>
    Pipeline de coleta de anúncios de imóveis na OLX, persistência no Supabase,
    geocodificação de CEPs e um modelo de Machine Learning que prevê o preço
    de mercado de cada imóvel e compara com o preço anunciado. Dashboard em
    Streamlit para visualizar os resultados, inclusive em mapa de calor.
  </p>

<!-- Badges -->
<p>
  <a href="https://github.com/jgabko/ImobData/graphs/contributors">
    <img src="https://img.shields.io/github/contributors/jgabko/ImobData" alt="contributors" />
  </a>
  <a href="">
    <img src="https://img.shields.io/github/last-commit/jgabko/ImobData" alt="last update" />
  </a>
  <a href="https://github.com/jgabko/ImobData/network/members">
    <img src="https://img.shields.io/github/forks/jgabko/ImobData" alt="forks" />
  </a>
  <a href="https://github.com/jgabko/ImobData/stargazers">
    <img src="https://img.shields.io/github/stars/jgabko/ImobData" alt="stars" />
  </a>
  <a href="https://github.com/jgabko/ImobData/issues/">
    <img src="https://img.shields.io/github/issues/jgabko/ImobData" alt="open issues" />
  </a>
</p>

<h4>
    <a href="https://github.com/jgabko/ImobData/">Ver Demo</a>
  <span> · </span>
    <a href="https://github.com/jgabko/ImobData">Documentação</a>
  <span> · </span>
    <a href="https://github.com/jgabko/ImobData/issues/">Reportar Bug</a>
  <span> · </span>
    <a href="https://github.com/jgabko/ImobData/issues/">Solicitar Feature</a>
  </h4>
</div>

<br />

<!-- Table of Contents -->
# Índice

- [Sobre o Projeto](#sobre-o-projeto)
  * [Arquitetura](#arquitetura)
  * [Tech Stack](#tech-stack)
  * [Funcionalidades](#funcionalidades)
- [Getting Started](#getting-started)
  * [Pré-requisitos](#pré-requisitos)
  * [Instalação](#instalação)
- [Estrutura de Arquivos](#estrutura-de-arquivos)
- [Roadmap](#roadmap)
- [Licença](#licença)


<!-- About the Project -->
## Sobre o Projeto

O **ImobData** raspa anúncios de imóveis publicados na OLX, salva os dados
brutos no Supabase, geocodifica os CEPs novos para alimentar um mapa de
calor e roda um modelo de Machine Learning treinado que prevê o preço de
mercado de cada imóvel. O preço previsto é comparado com o preço realmente
anunciado, e o imóvel é classificado como "acima do mercado", "abaixo do
mercado" ou "dentro da faixa esperada". Um dashboard em Streamlit reflete
esses resultados assim que o pipeline termina de rodar.

<!-- Architecture -->
### Arquitetura

```
OLX (scraper assíncrono) ──▶ validação/limpeza (Pydantic) ──▶ Supabase (imoveis_raw)
                                                                     │
                                              geocodificação de CEPs ┤
                                        modelo de ML (previsão de preço) ┤─▶ Supabase (comparação de preço)
                                                                     │
                                                              Streamlit dashboard
```

- **Scraping assíncrono**: o robô de extração roda de forma assíncrona contra
  a OLX e já valida/limpa os dados via Pydantic antes de persistir.
- **Precificação por ML**: um modelo treinado previamente (`treinar_modelo.py`)
  é carregado para prever o preço de mercado de cada imóvel pendente e
  comparar com o preço real anunciado.
- **Não bloqueante**: falhas na geocodificação ou na precificação não
  interrompem o pipeline; cada etapa é isolada com tratamento de exceções.

<!-- TechStack -->
### Tech Stack

<details>
  <summary>Coleta e Persistência</summary>
  <ul>
    <li><a href="https://www.python.org/">Python</a></li>
    <li><code>asyncio</code> (scraping assíncrono)</li>
    <li><a href="https://docs.pydantic.dev/">Pydantic</a> (validação/limpeza)</li>
    <li><a href="https://supabase.com/">Supabase</a> (persistência)</li>
  </ul>
</details>

<details>
  <summary>Machine Learning e Dashboard</summary>
  <ul>
    <li><a href="https://pandas.pydata.org/">pandas</a></li>
    <li><a href="https://joblib.readthedocs.io/">joblib</a> (carregamento do modelo)</li>
    <li>Modelo de ML treinado para precificação (scikit-learn ou similar)</li>
    <li><a href="https://streamlit.io/">Streamlit</a> (dashboard e mapa de calor)</li>
  </ul>
</details>

<!-- Features -->
### Funcionalidades

- Scraping assíncrono de anúncios de imóveis na OLX
- Validação e limpeza dos dados com Pydantic antes da persistência
- Persistência dos imóveis brutos no Supabase (`imoveis_raw`)
- Geocodificação automática de CEPs novos para o mapa de calor
- Previsão de preço de mercado via modelo de ML treinado
- Comparação entre preço previsto e preço anunciado, com classificação
  ("acima do mercado", "abaixo do mercado" ou "dentro da faixa esperada")
- Dashboard em Streamlit com os resultados atualizados após cada execução

<!-- Getting Started -->
## Getting Started

<!-- Prerequisites -->
### Pré-requisitos

Este projeto usa Python, além de um modelo de ML previamente treinado
(`treinar_modelo.py`, executado antes do pipeline de precificação) e uma
conta no Supabase configurada.

```bash
python --version
```

<!-- Installation -->
### Instalação

Clone o projeto

```bash
git clone https://github.com/jgabko/ImobData.git
cd ImobData
```

Instale as dependências

```bash
pip install -r requirements.txt
```

Gere os artefatos do modelo de precificação (`melhor_modelo_precificacao.pkl`,
`colunas_modelo.pkl` e `metricas_modelo.json`) rodando `treinar_modelo.py`
antes de executar o pipeline de precificação pela primeira vez.

<!-- File Structure -->
## Estrutura de Arquivos

```
ImobData/
├── pipeline.py                  # Orquestrador: scraping -> Supabase -> geocodificação -> ML -> dashboard
├── pipeline_precificacao.py     # Previsão de preço de mercado x preço anunciado
├── dashboard.py                 # Dashboard Streamlit
├── requirements.txt
│
├── scraping/                    # Coleta assíncrona de anúncios na OLX
│
├── processing/                  # Transformação e enriquecimento dos dados
│   ├── geocode/                    # Geocodificação de CEPs pendentes
│   └── ml_model/                   # Feature engineering e modelo de precificação
│
├── schema/                      # Validação (Pydantic) dos itens raspados
│
└── persistence/                 # Acesso a dados (Supabase)
```

<!-- Roadmap -->
## Roadmap

* [x] Scraping assíncrono de imóveis na OLX
* [x] Persistência dos dados brutos no Supabase
* [x] Geocodificação de CEPs para mapa de calor
* [x] Modelo de ML para previsão de preço de mercado
* [x] Dashboard Streamlit com comparação de preços
<!--* [ ] Re-treinamento automático periódico do modelo
* [ ] Alertas de oportunidades abaixo do mercado-->

<!-- License -->
## Licença

Distribuído sem licença definida. Veja LICENSE.txt para mais informações.
