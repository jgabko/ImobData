# scraping/olx_scraper.py
import asyncio
import logging
from typing import List, Optional
from urllib.parse import urljoin

from playwright.async_api import (
    async_playwright,
    Page,
    Locator,
    TimeoutError as PlaywrightTimeout,
)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from scraping.base_scraper import BaseScraper
from models.property import RawProperty
from config.settings import REQUEST_DELAY_SECONDS

logger = logging.getLogger(__name__)

_OLX_BASE = "https://www.olx.com.br"


class OLXScraper(BaseScraper):
    """
    Scraper concreto para OLX Brasil usando Playwright.

    Diferença fundamental em relação ao BeautifulSoup:
    - Opera sobre um browser real com JavaScript ativo.
    - Todos os métodos são async — retornam coroutines.
    - Usa Locators em vez de parsear HTML como string.
    """

    _LISTING_URL = "{base}/imoveis/venda/estado-{state}/{city}"

    def __init__(self, city: str, state: str, max_pages: int):
        super().__init__(city, state, max_pages)
        self._base_listing_url = self._LISTING_URL.format(
            base=_OLX_BASE,
            state=self.state,
            city=self.city,
        )

    # ── Público ──────────────────────────────────────────────────

    async def scrape(self) -> List[RawProperty]:
        """
        Abre o browser, itera pelas páginas e fecha tudo ao final.
        O `async with async_playwright()` garante que o processo
        do Chromium seja encerrado mesmo se uma exceção ocorrer.
        """
        all_properties: List[RawProperty] = []

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)

            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
                locale="pt-BR",
            )

            for page_number in range(1, self.max_pages + 1):
                url = self._build_url(page_number)
                logger.info(f"[OLX] Página {page_number}/{self.max_pages} → {url}")

                page = await context.new_page()
                try:
                    properties = await self._fetch_page_with_retry(page, url)

                    if not properties:
                        logger.info(
                            f"[OLX] Página {page_number} sem imóveis — encerrando."
                        )
                        break

                    all_properties.extend(properties)
                    logger.info(
                        f"[OLX] Página {page_number}: {len(properties)} imóveis | "
                        f"Total: {len(all_properties)}"
                    )

                except Exception as exc:
                    logger.error(
                        f"[OLX] Falha definitiva na página {page_number}: {exc}"
                    )
                    break

                finally:
                    await page.close()

                if page_number < self.max_pages:
                    await asyncio.sleep(REQUEST_DELAY_SECONDS)

            await browser.close()

        logger.info(f"[OLX] Extração concluída. Total: {len(all_properties)} imóveis")
        return all_properties

    # ── Privado: URL ─────────────────────────────────────────────

    def _build_url(self, page_number: int) -> str:
        if page_number == 1:
            return self._base_listing_url
        return f"{self._base_listing_url}?o={page_number}"

    # ── Privado: Navegação com Retry ─────────────────────────────

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((PlaywrightTimeout, ConnectionError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _fetch_page_with_retry(self, page: Page, url: str) -> List[RawProperty]:
        """
        Navega até a URL e aguarda os cards de imóveis aparecerem.
        Se o seletor não aparecer em 15s, PlaywrightTimeout é lançado
        e o Tenacity tenta novamente com backoff exponencial.
        """
        await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        await page.wait_for_selector(
            '[data-ds-component="DS-AdCard"]', timeout=15_000
        )
        return await self._parse_page(page)

    # ── Privado: Parsing ─────────────────────────────────────────

    async def _parse_page(self, page: Page) -> List[RawProperty]:
        """
        Coleta todos os cards visíveis na página e extrai dados de cada um.
        `locator.all()` materializa todos os elementos correspondentes
        ao seletor em uma lista de Locators individuais.
        """
        properties: List[RawProperty] = []
        cards = await page.locator('[data-ds-component="DS-AdCard"]').all()

        if not cards:
            logger.warning("[OLX] Nenhum card encontrado na página.")
            return []

        for card in cards:
            prop = await self._extract_property(card)
            if prop is not None:
                properties.append(prop)

        return properties

    # ── Privado: Extração de Imóvel ──────────────────────────────

    async def _extract_property(self, card: Locator) -> Optional[RawProperty]:
        """
        Extrai os campos brutos de um único card.
        Capturamos PlaywrightTimeout separado das outras exceções
        porque é o erro mais comum (elemento não carregou a tempo)
        e merece uma mensagem de log diferente.
        """
        try:
            title = await self._extract_title(card)
            raw_price = await self._extract_price(card)
            raw_area = await self._extract_area(card)
            neighborhood = await self._extract_neighborhood(card)
            url = await self._extract_url(card)

            return RawProperty(
                title=title,
                raw_price=raw_price,
                raw_area=raw_area,
                neighborhood=neighborhood,
                city=self.city,
                url=url,
                source="olx",
            )

        except PlaywrightTimeout:
            logger.warning("[OLX] Timeout ao extrair card — pulando")
            return None
        except Exception as exc:
            logger.debug(f"[OLX] Erro inesperado ao extrair card: {exc}")
            return None

    # ── Privado: Extratores de Campo ──────────────────────────────

    async def _extract_title(self, card: Locator) -> Optional[str]:
        for selector in ["h2", "h3", "[role='heading']"]:
            el = card.locator(selector)
            if await el.count() > 0:
                text = await el.first.inner_text(timeout=3_000)
                return text.strip() or None
        return None

    async def _extract_price(self, card: Locator) -> Optional[str]:
        for selector in [
            '[data-ds-component="DS-Text"][class*="price"]',
            '[class*="price"]',
        ]:
            el = card.locator(selector)
            if await el.count() > 0:
                text = await el.first.inner_text(timeout=3_000)
                if text.strip().startswith("R$"):
                    return text.strip()
        return None

    async def _extract_area(self, card: Locator) -> Optional[str]:
        all_texts = await card.locator("*").all_inner_texts()
        for text in all_texts:
            if ("m²" in text or "m2" in text.lower()) and len(text.strip()) < 20:
                return text.strip()
        return None

    async def _extract_neighborhood(self, card: Locator) -> Optional[str]:
        for testid in ["olx-adcard-location", "ad-card-location"]:
            el = card.locator(f'[data-testid="{testid}"]')
            if await el.count() > 0:
                text = await el.inner_text(timeout=3_000)
                return text.split(",")[0].strip() or None
        return None

    async def _extract_url(self, card: Locator) -> Optional[str]:
        link = card.locator("a").first
        href = await link.get_attribute("href", timeout=3_000)
        if href:
            return urljoin(_OLX_BASE, href)
        return None