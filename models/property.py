# models/property.py
from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class RawProperty(BaseModel):
    """
    Representa um imóvel ANTES da limpeza.
    Todos os campos são Optional[str] porque vêm do HTML —
    podem ser None ou mal-formatados.

    Não existe default para `source` aqui: cada scraper
    passa explicitamente ("olx", "zap", etc.), evitando
    que um imóvel seja marcado com a fonte errada por omissão.
    """
    title: Optional[str] = None
    raw_price: Optional[str] = None
    raw_area: Optional[str] = None
    neighborhood: Optional[str] = None
    city: Optional[str] = None
    url: Optional[str] = None
    source: str                                           # ← obrigatório, sem default
    scraped_at: datetime = Field(default_factory=datetime.utcnow)


class CleanProperty(BaseModel):
    """
    Representa um imóvel APÓS a limpeza e validação.
    Tipos são estritos: price é float, area é int, etc.
    """
    title: str
    price: float = Field(gt=0, description="Preço em R$, deve ser positivo")
    area_m2: int = Field(gt=0, description="Área em m², deve ser positivo")
    price_per_m2: float = Field(gt=0)
    neighborhood: str
    city: str
    url: str
    source: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    scraped_at: datetime

    @field_validator("neighborhood", "city", "title")
    @classmethod
    def strip_and_title_case(cls, v: str) -> str:
        return v.strip().title()

    @field_validator("price", "price_per_m2")
    @classmethod
    def round_two_decimals(cls, v: float) -> float:
        return round(v, 2)

    @model_validator(mode="after")
    def validate_price_per_m2_consistency(self) -> CleanProperty:
        expected = round(self.price / self.area_m2, 2)
        if abs(expected - self.price_per_m2) > 0.05:
            raise ValueError(
                f"price_per_m2 inconsistente: "
                f"calculado={expected}, recebido={self.price_per_m2}"
            )
        return self