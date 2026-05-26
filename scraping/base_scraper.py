# scraper/base_scraper.py
from abc import ABC, abstractmethod
from typing import List

from models.property import RawProperty
from scraper.http_client import HTTPClient


class BaseScraper(ABC):
    """
    Contrato base para todos os scrapers do pipeline.

    Mudança em relação à versão Playwright:
    - Recebe um HTTPClient injetado (Dependency Injection)
      em vez de criar seu próprio browser.
    - Isso permite trocar o client em testes (mock)
      sem alterar o scraper.
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