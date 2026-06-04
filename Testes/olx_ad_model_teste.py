from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator



class RawAdOlx(BaseModel):
    """
    
    
    """
    title: Optional[str] = None
    raw_price: Optional[str] = None
    raw_area: Optional[str] = None
    neighborhood: Optional[str] = None
    city: Optional[str] = None
    url: Optional[str] = None
    source: str                                           # ← obrigatório, sem default
    scraped_at: datetime = Field(default_factory=datetime.utcnow)

