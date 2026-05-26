# scraping/base_scraper.py
from abc import ABC, abstractmethod
from typing import List

from models.property import RawProperty
from scraping.http_client import HTTPClient          # ← era scraper.http_client


class BaseScraper(ABC):
    """
    Contrato base para todos os scrapers do pipeline.

    Recebe um HTTPClient injetado (Dependency Injection)
    em vez de gerenciar seu próprio mecanismo de transporte.
    Isso permite substituir o client em testes (mock)
    sem alterar nenhum scraper concreto.
    """

    def __init__(
        self,
        city: str,
        state: str,
        max_pages: int,
        http_client: HTTPClient,
    ):
        self.city = city
        self.state = state
        self.max_pages = max_pages
        self._client = http_client

    @abstractmethod
    def scrape(self) -> List[RawProperty]:
        """Executa a raspagem completa e retorna dados brutos."""
        ...

    @abstractmethod
    def _parse_page(self, html: str) -> List[RawProperty]:
        """Parseia o HTML de uma página de listagem."""
        ...