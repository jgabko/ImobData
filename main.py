# main.py
import asyncio
import logging
import sys

from config.settings import (
    TARGET_CITY, TARGET_STATE, MAX_PAGES,
    DATA_LAKE_PATH, DATA_WAREHOUSE_PATH,
)
from scraping.olx_scraper import OLXScraper
from transform.cleaner import PropertyCleaner
from storage.csv_writer import CSVWriter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("pipeline.log", encoding="utf-8"),
    ],
)

logger = logging.getLogger(__name__)


async def run_pipeline() -> None:
    logger.info("=" * 60)
    logger.info("PIPELINE DE ARBITRAGEM IMOBILIÁRIA — INICIADO")
    logger.info("=" * 60)

    # ── Etapa 1: Extração ──────────────────────────────────────
    logger.info("[Pipeline] Etapa 1/3 — Extração")
    scraper = OLXScraper(city=TARGET_CITY, state=TARGET_STATE, max_pages=MAX_PAGES)
    raw_properties = await scraper.scrape()

    # ── Etapa 2: Persistência bruta (Data Lake) ────────────────
    writer = CSVWriter(raw_path=DATA_LAKE_PATH, processed_path=DATA_WAREHOUSE_PATH)
    writer.write_raw(raw_properties)

    # ── Etapa 3: Transformação e Validação ─────────────────────
    logger.info("[Pipeline] Etapa 2/3 — Transformação")
    cleaner = PropertyCleaner()
    clean_properties = cleaner.clean(raw_properties)

    # ── Etapa 4: Persistência limpa ────────────────────────────
    logger.info("[Pipeline] Etapa 3/3 — Persistência")
    writer.write_clean(clean_properties)

    logger.info("=" * 60)
    logger.info(f"PIPELINE CONCLUÍDO | Brutos: {len(raw_properties)} | Limpos: {len(clean_properties)}")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_pipeline())