# scraper/olx_scraper.py
import logging
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from scraper.base_scraper import BaseScraper
from scraper.http_client import HTTPClient
from models.property import RawProperty

logger = logging.getLogger(__name__)

_OLX_BASE = "https://www.olx.com.br"


class OLXScraper(BaseScraper):
    """
    Scraper concreto para OLX Brasil usando BeautifulSoup.

    Estratégia de seleção de elementos:
    Priorizamos atributos 'data-*' e IDs estáveis em vez de
    classes CSS, que mudam a cada deploy do frontend.
    """

    _LISTING_URL = (
        "{base}/imoveis/venda/estado-{state}/{city}"
    )

    def __init__(
        self,
        city: str,
        state: str,
        max_pages: int,
        http_client: HTTPClient,
    ):
        super().__init__(city, state, max_pages, http_client)
        self._base_listing_url = self._LISTING_URL.format(
            base=_OLX_BASE,
            state=self.state,
            city=self.city,
        )

    # ── Público ──────────────────────────────────────────────────

    def scrape(self) -> List[RawProperty]:
        """
        Itera pelas páginas de listagem e acumula os imóveis.
        Encerra cedo se uma página vier vazia (fim da paginação).
        """
        all_properties: List[RawProperty] = []

        for page_number in range(1, self.max_pages + 1):
            url = self._build_url(page_number)
            logger.info(f"[OLX] Página {page_number}/{self.max_pages} → {url}")

            try:
                html = self._client.get(url)
            except Exception as exc:
                logger.error(f"[OLX] Falha ao buscar página {page_number}: {exc}")
                break

            properties = self._parse_page(html)

            if not properties:
                logger.info(f"[OLX] Página {page_number} sem imóveis — encerrando.")
                break

            all_properties.extend(properties)
            logger.info(
                f"[OLX] Página {page_number}: {len(properties)} imóveis | "
                f"Total: {len(all_properties)}"
            )

        return all_properties

    # ── Privado: Construção de URL ────────────────────────────────

    def _build_url(self, page_number: int) -> str:
        """
        OLX usa query param ?o=N para paginação.
        Página 1 não usa o parâmetro (URL limpa).
        """
        if page_number == 1:
            return self._base_listing_url
        return f"{self._base_listing_url}?o={page_number}"

    # ── Privado: Parsing ─────────────────────────────────────────

    def _parse_page(self, html: str) -> List[RawProperty]:
        """
        Parseia o HTML de uma página de listagem.

        BeautifulSoup recebe o HTML como string e o
        transforma em uma árvore de objetos navegável —
        o DOM em memória.
        """
        soup = BeautifulSoup(html, "lxml")
        cards = self._find_cards(soup)

        if not cards:
            logger.warning("[OLX] Nenhum card encontrado — estrutura do HTML pode ter mudado.")
            return []

        properties: List[RawProperty] = []
        for card in cards:
            prop = self._extract_property(card)
            if prop is not None:
                properties.append(prop)

        return properties

    def _find_cards(self, soup: BeautifulSoup) -> List[Tag]:
        """
        Localiza os cards de anúncios na página.

        Usamos uma busca por atributo data-ds-component porque
        é mais semântica e estável que seletores por classe CSS.
        Se não encontrar, tenta o seletor de fallback por section.
        """
        cards = soup.find_all(attrs={"data-ds-component": "DS-AdCard"})

        if not cards:
            # Fallback: estrutura mais genérica
            cards = soup.select("section[data-lurker-detail]")
            logger.debug(f"[OLX] Usando seletor fallback: {len(cards)} cards")

        return cards

    def _extract_property(self, card: Tag) -> Optional[RawProperty]:
        """
        Extrai os campos brutos de um único card de anúncio.

        Todo campo pode ser None — a ausência de dado é
        informação válida nesta etapa. A limpeza e rejeição
        acontecem no transformer.
        """
        try:
            title = self._extract_title(card)
            raw_price = self._extract_price(card)
            raw_area = self._extract_area(card)
            neighborhood = self._extract_neighborhood(card)
            url = self._extract_url(card)

            return RawProperty(
                title=title,
                raw_price=raw_price,
                raw_area=raw_area,
                neighborhood=neighborhood,
                city=self.city,
                url=url,
                source="olx",
            )

        except Exception as exc:
            logger.debug(f"[OLX] Erro ao extrair card: {exc}")
            return None

    # ── Privado: Extratores de Campo ──────────────────────────────

    def _extract_title(self, card: Tag) -> Optional[str]:
        """
        Tenta h2 primeiro (semântico), depois h3, depois
        qualquer elemento com role='heading'.
        """
        for selector in ["h2", "h3", "[role='heading']"]:
            el = card.select_one(selector)
            if el:
                return el.get_text(strip=True) or None
        return None

    def _extract_price(self, card: Tag) -> Optional[str]:
        """
        Preço na OLX fica em um elemento com texto começando em 'R$'.
        Percorre todos os elementos de texto e busca esse padrão.
        """
        for el in card.find_all(True):
            text = el.get_text(strip=True)
            if text.startswith("R$") and len(text) < 30:
                return text
        return None

    def _extract_area(self, card: Tag) -> Optional[str]:
        """
        Busca qualquer texto que contenha 'm²' ou 'm2'.
        A limpeza do número fica para o transformer.
        """
        for el in card.find_all(True):
            text = el.get_text(strip=True)
            if ("m²" in text or "m2" in text.lower()) and len(text) < 20:
                return text
        return None

    def _extract_neighborhood(self, card: Tag) -> Optional[str]:
        """
        Localização geralmente vem em um elemento com
        data-testid contendo 'location' ou 'address'.
        """
        for testid in ["olx-adcard-location", "ad-card-location"]:
            el = card.find(attrs={"data-testid": testid})
            if el:
                text = el.get_text(strip=True)
                return text.split(",")[0].strip() or None

        # Fallback: procura ícone de localização pelo SVG
        location_el = card.select_one("[class*='location'], [class*='address']")
        if location_el:
            return location_el.get_text(strip=True).split(",")[0].strip() or None

        return None

    def _extract_url(self, card: Tag) -> Optional[str]:
        """
        O link principal do card — sempre uma tag <a> com href.
        Usamos urljoin para garantir URL absoluta mesmo se
        o href vier como caminho relativo ('/imoveis/...').
        """
        link = card.find("a", href=True)
        if link:
            return urljoin(_OLX_BASE, link["href"])
        return None