# scraping/base_scraper.py
from abc import ABC, abstractmethod
from typing import List

from models.property import RawProperty


class BaseScraper(ABC):
    """
    Contrato base para todos os scrapers do pipeline.

    Na versão Playwright, não há HTTPClient externo injetado —
    cada scraper gerencia seu próprio browser internamente,
    pois o Playwright encapsula toda a lógica de transporte.

    Os métodos abstratos são async porque todas as operações
    do Playwright são I/O-bound e retornam coroutines.
    """

    def __init__(self, city: str, state: str, max_pages: int):
        self.city = city
        self.state = state
        self.max_pages = max_pages

    @abstractmethod
    async def scrape(self) -> List[RawProperty]:
        """Executa a raspagem completa e retorna dados brutos."""
        ...

    @abstractmethod
    async def _parse_page(self, page) -> List[RawProperty]:
        """
        Parseia uma página já carregada no browser.
        Recebe um objeto Page do Playwright (não HTML como string).
        """
        ...