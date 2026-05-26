# storage/csv_writer.py
import os
import logging
from datetime import datetime
from typing import List

import pandas as pd

from models.property import RawProperty, CleanProperty

logger = logging.getLogger(__name__)


class CSVWriter:
    """
    Responsável por persistir dados no Data Lake (CSV local).
    Separa dados brutos de dados limpos em diretórios distintos.
    """

    def __init__(self, raw_path: str, processed_path: str):
        self.raw_path = raw_path
        self.processed_path = processed_path
        os.makedirs(raw_path, exist_ok=True)
        os.makedirs(processed_path, exist_ok=True)

    def _today_filename(self, prefix: str) -> str:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        return f"{prefix}_{today}.csv"

    def write_raw(self, properties: List[RawProperty]) -> str:
        filename = self._today_filename("raw_olx")
        filepath = os.path.join(self.raw_path, filename)
        records = [p.model_dump() for p in properties]
        df = pd.DataFrame(records)
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        logger.info(f"[CSVWriter] {len(records)} registros brutos salvos em '{filepath}'")
        return filepath

    def write_clean(self, properties: List[CleanProperty]) -> str:
        filename = self._today_filename("clean_olx")
        filepath = os.path.join(self.processed_path, filename)
        records = [p.model_dump() for p in properties]
        df = pd.DataFrame(records)
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        logger.info(f"[CSVWriter] {len(records)} registros limpos salvos em '{filepath}'")
        return filepath