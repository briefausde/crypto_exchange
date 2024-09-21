from decimal import Decimal

from pydantic import BaseModel


class ConvertRequest(BaseModel):
    currency_from: str
    currency_to: str
    amount: Decimal
    exchange: str | None = None
    cache_max_seconds: int | None = None


class ConvertResponse(BaseModel):
    currency_from: str
    currency_to: str
    exchange: str
    rate: str
    result: str
    updated_at: int
