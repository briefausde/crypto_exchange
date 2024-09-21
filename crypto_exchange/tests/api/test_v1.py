import aiohttp
import pytest
from aiohttp import web
from unittest.mock import AsyncMock

from crypto_exchange.api.v1 import convert
from crypto_exchange.exchange.exceptions import (
    InvalidAssetAmount,
    ProviderBadResponse,
    PairNotFound,
    InvalidProvider,
)
from crypto_exchange.exchange.schemas import ExchangeResult


@pytest.fixture
def client(mocker, aiohttp_client, loop):
    app = web.Application()

    app["http_session"] = mocker.MagicMock(spec=aiohttp.ClientSession)
    app["redis"] = AsyncMock()

    app.router.add_post("/convert", convert)

    return loop.run_until_complete(aiohttp_client(app))


async def test_convert_success(client, mocker):
    mock_resolver = mocker.patch("crypto_exchange.api.v1.ExchangeResolver")
    mock_resolver.return_value.resolve = AsyncMock(
        return_value=ExchangeResult(
            rate="50000",
            result="50000",
            updated_at=1633024800,
        )
    )
    mock_resolver.return_value.exchange = "binance"

    payload = {
        "currency_from": "BTC",
        "currency_to": "USDT",
        "amount": 1,
        "exchange": "binance",
        "cache_max_seconds": 300
    }

    response = await client.post("/convert", json=payload)

    assert response.status == 200
    data = await response.json()
    assert data["currency_from"] == "BTC"
    assert data["currency_to"] == "USDT"
    assert data["rate"] == "50000"
    assert data["result"] == "50000"


async def test_convert_invalid_request_format(client):
    response = await client.post("/convert", data="invalid_json")
    assert response.status == 400
    data = await response.json()
    assert "error" in data


async def test_convert_invalid_provider(client, mocker):
    mock_resolver = mocker.patch("crypto_exchange.api.v1.ExchangeResolver")
    mock_resolver.return_value.resolve = AsyncMock(
        side_effect=InvalidProvider("Invalid provider")
    )

    payload = {
        "currency_from": "BTC",
        "currency_to": "USDT",
        "amount": 1,
        "exchange": "invalid_exchange",
        "cache_max_seconds": 300
    }

    response = await client.post("/convert", json=payload)
    assert response.status == 400
    data = await response.json()
    assert data["error"] == "Invalid provider"


async def test_convert_invalid_asset_amount(client, mocker):
    mock_resolver = mocker.patch("crypto_exchange.api.v1.ExchangeResolver")
    mock_resolver.return_value.resolve = AsyncMock(
        side_effect=InvalidAssetAmount("Invalid asset amount")
    )

    payload = {
        "currency_from": "BTC",
        "currency_to": "USDT",
        "amount": 0.00001,
        "exchange": "binance",
        "cache_max_seconds": 300
    }

    response = await client.post("/convert", json=payload)
    assert response.status == 400
    data = await response.json()
    assert data["error"] == "Invalid asset amount"


async def test_convert_pair_not_found(client, mocker):
    mock_resolver = mocker.patch("crypto_exchange.api.v1.ExchangeResolver")
    mock_resolver.return_value.resolve = AsyncMock(
        side_effect=PairNotFound("Pair not found")
    )

    payload = {
        "currency_from": "BTC",
        "currency_to": "XYZ",
        "amount": 1,
        "exchange": "binance",
        "cache_max_seconds": 300
    }

    response = await client.post("/convert", json=payload)
    assert response.status == 400
    data = await response.json()
    assert data["error"] == "Pair not found"


async def test_convert_provider_bad_response(client, mocker):
    mock_resolver = mocker.patch("crypto_exchange.api.v1.ExchangeResolver")
    mock_resolver.return_value.resolve = AsyncMock(
        side_effect=ProviderBadResponse()
    )

    payload = {
        "currency_from": "BTC",
        "currency_to": "USDT",
        "amount": 1,
        "exchange": "binance",
        "cache_max_seconds": 300
    }

    response = await client.post("/convert", json=payload)
    assert response.status == 500
    data = await response.json()
    assert data["error"] == "Error with exchange, please try again later."


async def test_convert_internal_error(client, mocker):
    mock_resolver = mocker.patch("crypto_exchange.api.v1.ExchangeResolver")
    mock_resolver.return_value.resolve = AsyncMock(
        side_effect=Exception("Unexpected error")
    )

    payload = {
        "currency_from": "BTC",
        "currency_to": "USDT",
        "amount": 1,
        "exchange": "binance",
        "cache_max_seconds": 300
    }

    response = await client.post("/convert", json=payload)
    assert response.status == 500
    data = await response.json()
    assert data["error"] == "Internal error, try later..."
