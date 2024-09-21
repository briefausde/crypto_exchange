from datetime import datetime
from decimal import Decimal
import pytest
import json

import redis.asyncio as aioredis
from aiohttp import ClientSession

from crypto_exchange.config import get_config
from crypto_exchange.exchange.schemas import ExchangeInfo, ExchangeRate
from crypto_exchange.exchange.providers.abc import Provider


@pytest.fixture
async def redis_client():
    config = get_config()
    redis = await aioredis.from_url(
        f"redis://{config.redis_host}:{config.redis_port}"
    )
    await redis.flushdb()
    yield redis
    await redis.close()


@pytest.fixture
async def http_session():
    async with ClientSession() as session:
        yield session


class MockProvider(Provider):

    def _handle_api_error(self, url: str, status: int, data: dict) -> None:
        pass

    async def _fetch_exchange_info(
        self,
        currency_from: str,
        currency_to: str,
    ) -> ExchangeInfo:
        return ExchangeInfo(
            based_ticker=f"{currency_from}{currency_to}",
            from_asset_min_amount=Decimal("0.01"),
            from_asset_max_amount=Decimal("100.0"),
            to_asset_min_amount=Decimal("0.01"),
            to_asset_max_amount=Decimal("100.0"),
            timestamp=int(datetime.utcnow().timestamp()),
        )

    async def _fetch_ticker_price(self, based_ticker: str) -> Decimal:
        return Decimal("50000.0")

    @staticmethod
    def get_ticker(currency_from: str, currency_to: str) -> str:
        return f"{currency_from}{currency_to}"


async def test_get_exchange_info_and_redis_storage(redis_client, http_session):
    provider = MockProvider(http_session, redis_client)

    exchange_info = await provider.get_exchange_info(
        "BTC", "USDT", cache_max_seconds=60
    )

    assert exchange_info.based_ticker == "BTCUSDT"
    assert exchange_info.from_asset_min_amount == Decimal("0.01")

    cache_key = provider._get_exchange_info_cache_key("BTCUSDT")
    cached_value = await redis_client.get(cache_key)

    assert cached_value is not None
    cached_exchange_info = ExchangeInfo(**json.loads(cached_value))

    assert cached_exchange_info.based_ticker == "BTCUSDT"
    assert cached_exchange_info.from_asset_min_amount == Decimal("0.01")


async def test_get_exchange_rate_and_redis_storage(redis_client, http_session):
    provider = MockProvider(http_session, redis_client)

    exchange_rate = await provider.get_exchange_rate(
        "BTCUSDT", "BTC", "USDT", cache_max_seconds=60
    )

    assert exchange_rate.rate == Decimal("50000.0")

    cache_key = provider._get_exchange_rate_cache_key("BTCUSDT")
    cached_value = await redis_client.get(cache_key)

    assert cached_value is not None
    cached_exchange_rate = ExchangeRate(**json.loads(cached_value))

    assert cached_exchange_rate.rate == Decimal("50000.0")
