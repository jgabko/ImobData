# transformer/cleaner.py
import re
import logging
from typing import List, Optional

import pandas as pd
from pydantic import ValidationError

from models.property import RawProperty, CleanProperty

logger = logging.getLogger(__name__)


class PropertyCleaner:
    """
    Recebe uma lista de RawProperty e retorna uma lista de CleanProperty.
    Responsabilidade única: transformar e validar dados, não salvar nem alertar.
    """

    PRICE_PATTERN = re.compile(r"[\d.,]+")
    AREA_PATTERN = re.compile(r"(\d+(?:[.,]\d+)?)\s*m[²2]", re.IGNORECASE)

    def clean(self, raw_properties: List[RawProperty]) -> List[CleanProperty]:
        df = self._to_dataframe(raw_properties)
        df = self._apply_transformations(df)
        df = self._drop_invalid_rows(df)
        df = self._deduplicate(df)
        return self._to_models(df)

    def _to_dataframe(self, properties: List[RawProperty]) -> pd.DataFrame:
        records = [p.model_dump() for p in properties]
        return pd.DataFrame(records)

    def _apply_transformations(self, df: pd.DataFrame) -> pd.DataFrame:
        df["price"] = df["raw_price"].apply(self._parse_price)
        df["area_m2"] = df["raw_area"].apply(self._parse_area)
        df["price_per_m2"] = df.apply(self._calculate_price_per_m2, axis=1)
        return df

    def _parse_price(self, raw: Optional[str]) -> Optional[float]:
        if not raw:
            return None
        cleaned = raw.replace("R$", "").replace("\xa0", "").strip()
        match = self.PRICE_PATTERN.search(cleaned)
        if not match:
            return None
        number_str = match.group().replace(".", "").replace(",", ".")
        try:
            return float(number_str)
        except ValueError:
            return None

    def _parse_area(self, raw: Optional[str]) -> Optional[int]:
        if not raw:
            return None
        match = self.AREA_PATTERN.search(raw)
        if not match:
            return None
        number_str = match.group(1).replace(",", ".")
        try:
            return int(float(number_str))
        except ValueError:
            return None

    def _calculate_price_per_m2(self, row: pd.Series) -> Optional[float]:
        price = row.get("price")
        area = row.get("area_m2")
        if price and area and area > 0:
            return round(price / area, 2)
        return None

    def _drop_invalid_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        before = len(df)
        df = df.dropna(subset=["price", "area_m2", "price_per_m2", "neighborhood", "title"])
        df = df[df["price"] > 10_000]
        df = df[df["area_m2"] > 10]
        df = df[df["price_per_m2"] < 50_000]
        after = len(df)
        logger.info(f"[Cleaner] Removidas {before - after} linhas inválidas")
        return df

    def _deduplicate(self, df: pd.DataFrame) -> pd.DataFrame:
        before = len(df)
        df = df.drop_duplicates(subset=["url"])
        df = df.drop_duplicates(subset=["title", "price", "area_m2", "neighborhood"])
        after = len(df)
        logger.info(f"[Cleaner] Removidas {before - after} duplicatas")
        return df

    def _to_models(self, df: pd.DataFrame) -> List[CleanProperty]:
        clean: List[CleanProperty] = []
        for _, row in df.iterrows():
            try:
                prop = CleanProperty(
                    title=row["title"],
                    price=row["price"],
                    area_m2=int(row["area_m2"]),
                    price_per_m2=row["price_per_m2"],
                    neighborhood=row["neighborhood"],
                    city=row["city"],
                    url=row["url"],
                    source=row["source"],
                    scraped_at=row["scraped_at"],
                )
                clean.append(prop)
            except ValidationError as exc:
                logger.warning(f"[Cleaner] Validação falhou para '{row.get('title')}': {exc}")
        logger.info(f"[Cleaner] {len(clean)} imóveis válidos após limpeza")
        return clean