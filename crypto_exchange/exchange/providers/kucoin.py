import logging
from decimal import Decimal
from datetime import datetime

from crypto_exchange.exchange.exceptions import (
    PairNotFound,
    ProviderBadResponse,
)
from crypto_exchange.exchange.providers.abc import Provider
from crypto_exchange.exchange.schemas import ExchangeInfo

log = logging.getLogger(__name__)

BASE_URL = "https://api.kucoin.com"

EXCHANGE_INFO_URL = f"{BASE_URL}/api/v2/symbols/{{ticker}}"

TICKER_PRICE_URL = (
    f"{BASE_URL}/api/v1/market/orderbook/level1?symbol={{ticker}}"
)

PAIR_NOT_FOUND_ERROR_CODE = "900001"


class Kucoin(Provider):
    """Kucoin cryptocurrency exchange provider."""

    def _handle_api_error(self, url: str, status: int, data: dict) -> None:
        error_code = data.get("code")
        if error_code == PAIR_NOT_FOUND_ERROR_CODE:
            raise PairNotFound("Pair not found.")
        if status != 200:
            log.warning(f"Kucoin returns status code {status} for url {url}")
            raise ProviderBadResponse()

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

        try:
            asset_info = data["data"]
        except KeyError:
            log.warning(f"Kucoin returned bad response: {data}")
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
