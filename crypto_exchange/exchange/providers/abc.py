import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Any

import redis.asyncio as aioredis
from aiohttp import ClientSession

from crypto_exchange.exchange.exceptions import (
    InvalidAssetAmount,
    PairNotFound,
    ProviderBadResponse,
)
from crypto_exchange.exchange.schemas import (
    ExchangeInfo,
    ExchangeRate,
    ExchangeResult,
)
from crypto_exchange.lib.utils import DecimalEncoder, format_decimal

logger = logging.getLogger(__name__)


class Provider(ABC):
    """Abstract base class for cryptocurrency providers."""

    NOT_FOUND_ERROR_CODES: list[int | str] = []

    def __init__(self, http_session: ClientSession, redis: aioredis.Redis):
        self.name = self.__class__.__name__
        self.http_session = http_session
        self.redis = redis

    async def _fetch_data(self, url: str) -> Any:
        async with self.http_session.get(url) as response:
            data = await response.json()
            self._handle_api_error(url, response.status, data)
            return data

    def _handle_api_error(self, url: str, status: int, data: dict) -> None:
        if (
            isinstance(data, dict)
            and data.get("code") in self.NOT_FOUND_ERROR_CODES
        ):
            raise PairNotFound("Pair not found.")
        if status != 200:
            logger.warning(
                f"{self.name} returns status code {status} for url {url}"
            )
            raise ProviderBadResponse()

    @abstractmethod
    async def _fetch_exchange_info(
        self,
        currency_from: str,
        currency_to: str,
    ) -> ExchangeInfo:
        """Fetch exchange information from the provider's API."""
        raise NotImplementedError()

    @abstractmethod
    async def _fetch_ticker_price(self, based_ticker: str) -> Decimal:
        """Fetch the ticker price from the provider's API."""
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def get_ticker(currency_from: str, currency_to: str) -> str:
        """Construct the ticker symbol for the currency pair."""
        raise NotImplementedError()

    @staticmethod
    def _is_fresh_cache_data(
        cache_timestamp: int,
        cache_max_seconds: int | None,
    ) -> bool:
        if cache_max_seconds is None:
            return False
        timestamp_now = int(datetime.utcnow().timestamp())
        return cache_timestamp >= timestamp_now - cache_max_seconds

    def _check_exchange_amount(
        self,
        exchange_info: ExchangeInfo,
        amount: Decimal,
        currency_from: str,
        currency_to: str,
    ) -> None:
        """Check if the amount is within the exchange's allowed limits."""

        ticker = self.get_ticker(currency_from, currency_to)
        if ticker == exchange_info.based_ticker:
            min_amount = exchange_info.from_asset_min_amount
            max_amount = exchange_info.from_asset_max_amount
        else:
            min_amount = exchange_info.to_asset_min_amount
            max_amount = exchange_info.to_asset_max_amount

        if not (min_amount <= amount <= max_amount):
            raise InvalidAssetAmount(
                f"Amount {amount} is outside the allowed range: "
                f"{min_amount} - {max_amount}"
            )

    async def get_exchange_info(
        self,
        currency_from: str,
        currency_to: str,
        cache_max_seconds: int | None,
    ) -> ExchangeInfo:
        """Fetch or retrieve cached exchange between two currencies."""

        if cache_max_seconds is not None:
            tickers = [
                self.get_ticker(currency_from, currency_to),
                self.get_ticker(currency_to, currency_from),
            ]
            exchange_info = await self._get_cached_exchange_info(
                tickers=tickers,
                cache_max_seconds=cache_max_seconds,
            )
            if exchange_info:
                return exchange_info

        exchange_info = await self._fetch_exchange_info(
            currency_from=currency_from,
            currency_to=currency_to,
        )
        await self._set_exchange_info_cache(
            ticker=exchange_info.based_ticker,
            exchange_info=exchange_info,
        )
        return exchange_info

    def _get_exchange_info_cache_key(self, key: str) -> str:
        """Generate a cache key for exchange information."""
        return f"{self.name}-exchange-info-{key}"

    async def _set_exchange_info_cache(
        self,
        ticker: str,
        exchange_info: ExchangeInfo,
    ) -> None:
        """Set the exchange information in cache."""
        cache_key = self._get_exchange_info_cache_key(ticker)
        await self.redis.set(
            cache_key, json.dumps(exchange_info.dict(), cls=DecimalEncoder)
        )

    async def _get_cached_exchange_info(
        self,
        tickers: list[str],
        cache_max_seconds: int | None,
    ) -> ExchangeInfo | None:
        """Retrieve cached exchange information if available and fresh."""

        cache_keys = [
            self._get_exchange_info_cache_key(ticker) for ticker in tickers
        ]
        cached_values = await self.redis.mget(cache_keys)
        for cached_value in cached_values:
            if not cached_value:
                continue
            exchange_info = ExchangeInfo.model_validate_json(cached_value)
            if self._is_fresh_cache_data(
                cache_timestamp=exchange_info.timestamp,
                cache_max_seconds=cache_max_seconds,
            ):
                return exchange_info
        return None

    async def get_exchange_rate(
        self,
        based_ticker: str,
        currency_from: str,
        currency_to: str,
        cache_max_seconds: int | None,
    ) -> ExchangeRate:
        """Fetch or retrieve cached exchange rate for the given ticker."""

        if cache_max_seconds is not None:
            exchange_rate = await self._get_cached_exchange_rate(
                ticker=based_ticker,
                cache_max_seconds=cache_max_seconds,
            )
            if exchange_rate:
                return exchange_rate

        price = await self._fetch_ticker_price(based_ticker)
        exchange_rate = ExchangeRate(
            rate=Decimal(price),
            timestamp=int(datetime.utcnow().timestamp()),
        )

        await self._set_exchange_rate_cache(based_ticker, exchange_rate)

        if self.get_ticker(currency_from, currency_to) != based_ticker:
            exchange_rate.rate = 1 / exchange_rate.rate

        return exchange_rate

    def _get_exchange_rate_cache_key(self, key: str) -> str:
        """Generate a cache key for exchange rate."""
        return f"{self.name}-exchange-rate-{key}"

    async def _set_exchange_rate_cache(
        self,
        ticker: str,
        exchange_rate: ExchangeRate,
    ) -> None:
        """Set the exchange rate in cache."""
        cache_key = self._get_exchange_rate_cache_key(ticker)
        await self.redis.set(
            cache_key, json.dumps(exchange_rate.dict(), cls=DecimalEncoder)
        )

    async def _get_cached_exchange_rate(
        self,
        ticker: str,
        cache_max_seconds: int | None,
    ) -> ExchangeRate | None:
        """Retrieve cached exchange rate if available and fresh."""

        cache_key = self._get_exchange_rate_cache_key(ticker)
        cached_value = await self.redis.get(cache_key)
        if cached_value:
            exchange_rate = ExchangeRate.model_validate_json(cached_value)
            if self._is_fresh_cache_data(
                cache_timestamp=exchange_rate.timestamp,
                cache_max_seconds=cache_max_seconds,
            ):
                return exchange_rate

        return None

    async def exchange(
        self,
        amount: Decimal,
        currency_from: str,
        currency_to: str,
        cache_max_seconds: int | None,
    ) -> ExchangeResult:
        """
        Fetch or retrieve cached exchange rate and returns the exchange result.
        """
        exchange_info = await self.get_exchange_info(
            currency_from=currency_from,
            currency_to=currency_to,
            cache_max_seconds=cache_max_seconds,
        )
        self._check_exchange_amount(
            exchange_info=exchange_info,
            amount=amount,
            currency_from=currency_from,
            currency_to=currency_to,
        )
        exchange_rate = await self.get_exchange_rate(
            based_ticker=exchange_info.based_ticker,
            currency_from=currency_from,
            currency_to=currency_to,
            cache_max_seconds=cache_max_seconds,
        )
        return ExchangeResult(
            rate=format_decimal(exchange_rate.rate),
            result=format_decimal(amount * exchange_rate.rate),
            updated_at=exchange_rate.timestamp,
        )
