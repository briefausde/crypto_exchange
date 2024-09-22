import logging
from datetime import datetime
from decimal import Decimal

from crypto_exchange.exchange.exceptions import (
    PairNotFound,
    ProviderBadResponse,
)
from crypto_exchange.exchange.providers.abc import Provider
from crypto_exchange.exchange.schemas import ExchangeInfo

logger = logging.getLogger(__name__)

BASE_URL = "https://api.kucoin.com"

EXCHANGE_INFO_URL = f"{BASE_URL}/api/v2/symbols/{{ticker}}"

TICKER_PRICE_URL = (
    f"{BASE_URL}/api/v1/market/orderbook/level1?symbol={{ticker}}"
)

PAIR_NOT_FOUND_ERROR_CODE = "900001"


class Kucoin(Provider):
    """Kucoin cryptocurrency exchange provider."""

    NOT_FOUND_ERROR_CODES = [PAIR_NOT_FOUND_ERROR_CODE]

    async def _fetch_exchange_info(
        self,
        currency_from: str,
        currency_to: str,
    ) -> ExchangeInfo:

        async def _fetch(ticker: str) -> dict:
            return await self._fetch_data(
                EXCHANGE_INFO_URL.format(ticker=ticker)
            )

        ticker = f"{currency_from}-{currency_to}"
        try:
            data = await _fetch(ticker)
        except PairNotFound:
            ticker = f"{currency_to}-{currency_from}"
            data = await _fetch(ticker)

        asset_info = data.get("data")
        if not asset_info:
            logger.warning(f"Kucoin returned bad response: {data}")
            raise ProviderBadResponse()

        return ExchangeInfo(
            based_ticker=ticker,
            from_asset_min_amount=Decimal(asset_info["baseMinSize"]),
            from_asset_max_amount=Decimal(asset_info["baseMaxSize"]),
            to_asset_min_amount=Decimal(asset_info["baseMinSize"]),
            to_asset_max_amount=Decimal(asset_info["baseMaxSize"]),
            timestamp=int(datetime.utcnow().timestamp()),
        )

    async def _fetch_ticker_price(self, based_ticker: str) -> Decimal:
        data = await self._fetch_data(
            TICKER_PRICE_URL.format(ticker=based_ticker)
        )
        return Decimal(data["data"]["price"])

    @staticmethod
    def get_ticker(currency_from: str, currency_to: str) -> str:
        return f"{currency_from}-{currency_to}"
