from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from crypto_exchange.exchange.exceptions import (
    PairNotFound,
    ProviderBadResponse,
)
from crypto_exchange.exchange.providers.binance import Binance

BASE_TICKER = "BTCUSDT"
MOCK_EXCHANGE_INFO = {
    "fromAsset": "BTC",
    "toAsset": "USDT",
    "fromAssetMinAmount": "0.001",
    "fromAssetMaxAmount": "100",
    "toAssetMinAmount": "10",
    "toAssetMaxAmount": "10000",
    "fromIsBase": True,
}


@pytest.fixture
def binance_provider():
    mock_http_session = AsyncMock()
    mock_redis = AsyncMock()
    return Binance(http_session=mock_http_session, redis=mock_redis)


async def test_fetch_exchange_info_success(binance_provider):
    binance_provider._fetch_data = AsyncMock(return_value=[MOCK_EXCHANGE_INFO])

    exchange_info = await binance_provider._fetch_exchange_info("BTC", "USDT")

    assert exchange_info.based_ticker == "BTCUSDT"
    assert exchange_info.from_asset_min_amount == Decimal("0.001")
    assert exchange_info.from_asset_max_amount == Decimal("100")
    assert exchange_info.to_asset_min_amount == Decimal("10")
    assert exchange_info.to_asset_max_amount == Decimal("10000")
    assert isinstance(exchange_info.timestamp, int)


async def test_fetch_ticker_price_success(binance_provider):
    mock_data = {"price": "56789.12345678"}
    binance_provider._fetch_data = AsyncMock(return_value=mock_data)

    price = await binance_provider._fetch_ticker_price("BTCUSDT")

    assert price == Decimal("56789.12345678")


async def test_handle_api_error(binance_provider):
    mock_data = {"code": 345122}
    with pytest.raises(PairNotFound):
        binance_provider._handle_api_error("some_url", 404, mock_data)

    mock_data = {"code": -1121}
    with pytest.raises(PairNotFound):
        binance_provider._handle_api_error("some_url", 404, mock_data)

    mock_data = {}
    with pytest.raises(ProviderBadResponse):
        binance_provider._handle_api_error("some_url", 500, mock_data)


async def test_get_ticker():
    ticker = Binance.get_ticker("BTC", "USDT")
    assert ticker == "BTCUSDT"
