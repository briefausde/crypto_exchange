from decimal import Decimal
from pydantic import BaseModel


class ExchangeInfo(BaseModel):
    based_ticker: str
    from_asset_min_amount: Decimal
    from_asset_max_amount: Decimal
    to_asset_min_amount: Decimal
    to_asset_max_amount: Decimal
    timestamp: int


class ExchangeRate(BaseModel):
    rate: Decimal
    timestamp: int


class ExchangeResult(BaseModel):
    rate: str
    result: str
    updated_at: int
