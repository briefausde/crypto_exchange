import pytest
from decimal import Decimal
from unittest.mock import AsyncMock

from crypto_exchange.exchange.providers.kucoin import Kucoin

BASE_TICKER = "BTC-USDT"
INTERMEDIARY_CURRENCIES = ["USDT", "BTC"]


@pytest.fixture
def kucoin_provider():
    mock_http_session = AsyncMock()
    mock_redis = AsyncMock()
    return Kucoin(http_session=mock_http_session, redis=mock_redis)


async def test_fetch_exchange_info_success(kucoin_provider):
    mock_data = {
        "data": {
            "baseMinSize": "0.001",
            "baseMaxSize": "100",
        }
    }
    kucoin_provider._fetch_data = AsyncMock(return_value=mock_data)

    exchange_info = await kucoin_provider._fetch_exchange_info("BTC", "USDT")

    assert exchange_info.based_ticker == "BTC-USDT"
    assert exchange_info.from_asset_min_amount == Decimal("0.001")
    assert exchange_info.from_asset_max_amount == Decimal("100")
    assert isinstance(exchange_info.timestamp, int)


async def test_fetch_ticker_price_success(kucoin_provider):
    mock_data = {
        "data": {
            "price": "56789.12345678",
        }
    }
    kucoin_provider._fetch_data = AsyncMock(return_value=mock_data)

    price = await kucoin_provider._fetch_ticker_price("BTC-USDT")

    assert price == Decimal("56789.12345678")


async def test_get_ticker():
    ticker = Kucoin.get_ticker("BTC", "USDT")
    assert ticker == "BTC-USDT"
