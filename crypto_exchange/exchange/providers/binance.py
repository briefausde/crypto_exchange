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

BASE_URL = "https://api.binance.com"

EXCHANGE_INFO_URL = (
    f"{BASE_URL}/sapi/v1/convert/exchangeInfo?fromAsset="
    f"{{currency_from}}&toAsset={{currency_to}}"
)

TICKER_PRICE_URL = f"{BASE_URL}/api/v3/ticker/price?symbol={{ticker}}"

PAIR_NOT_FOUND_ERROR_CODE = 345122
INVALID_SYMBOL_ERROR_CODE = -1121


class Binance(Provider):
    """Binance cryptocurrency exchange provider."""

    def _handle_api_error(self, url: str, status: int, data: dict) -> None:
        if status == 200:
            return
        error_code = data.get("code")
        if error_code in [PAIR_NOT_FOUND_ERROR_CODE, INVALID_SYMBOL_ERROR_CODE]:
            raise PairNotFound("Pair not found.")
        raise ProviderBadResponse()

    async def _fetch_exchange_info(
        self,
        currency_from: str,
        currency_to: str,
    ) -> ExchangeInfo:
        data = await self._fetch_data(
            EXCHANGE_INFO_URL.format(
                currency_from=currency_from,
                currency_to=currency_to,
            )
        )
        try:
            asset_info = data[0]
        except IndexError:
            raise ProviderBadResponse()

        if asset_info["fromIsBase"]:
            return ExchangeInfo(
                based_ticker=self.get_ticker(
                    asset_info["fromAsset"], asset_info["toAsset"]
                ),
                from_asset_min_amount=Decimal(asset_info["fromAssetMinAmount"]),
                from_asset_max_amount=Decimal(asset_info["fromAssetMaxAmount"]),
                to_asset_min_amount=Decimal(asset_info["toAssetMinAmount"]),
                to_asset_max_amount=Decimal(asset_info["toAssetMaxAmount"]),
                timestamp=int(datetime.utcnow().timestamp()),
            )

        return ExchangeInfo(
            based_ticker=self.get_ticker(
                asset_info["toAsset"], asset_info["fromAsset"]
            ),
            from_asset_min_amount=Decimal(asset_info["toAssetMinAmount"]),
            from_asset_max_amount=Decimal(asset_info["toAssetMaxAmount"]),
            to_asset_min_amount=Decimal(asset_info["fromAssetMinAmount"]),
            to_asset_max_amount=Decimal(asset_info["fromAssetMaxAmount"]),
            timestamp=int(datetime.utcnow().timestamp()),
        )

    async def _fetch_ticker_price(self, based_ticker: str) -> Decimal:
        data = await self._fetch_data(
            TICKER_PRICE_URL.format(ticker=based_ticker)
        )
        return Decimal(data["price"])

    @staticmethod
    def get_ticker(currency_from: str, currency_to: str) -> str:
        return f"{currency_from}{currency_to}"
