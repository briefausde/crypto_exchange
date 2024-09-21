import logging
import redis.asyncio as aioredis
from decimal import Decimal
from aiohttp import ClientSession

from crypto_exchange.exchange.providers.binance import Binance
from crypto_exchange.exchange.providers.kucoin import Kucoin
from crypto_exchange.exchange.schemas import ExchangeResult
from crypto_exchange.lib.constants import INTERMEDIARY_CURRENCIES
from crypto_exchange.exchange.exceptions import (
    PairNotFound,
    InvalidProvider,
)
from crypto_exchange.lib.utils import format_decimal

log = logging.getLogger(__name__)

PROVIDERS_MAP = {
    "binance": Binance,
    "kucoin": Kucoin,
}


class ExchangeResolver:
    def __init__(
        self, http_session: ClientSession,
        redis: aioredis.Redis,
        exchange: str | None,
    ):
        self.http_session = http_session
        self.redis = redis
        self.exchange = exchange

    def get_provider_instance(self) -> Binance | Kucoin:
        try:
            provider_cls = PROVIDERS_MAP[self.exchange.lower()]
        except KeyError:
            raise InvalidProvider(
                f"Provider '{self.exchange}' is not supported."
            )
        return provider_cls(
            http_session=self.http_session,
            redis=self.redis,
        )

    async def resolve(
        self,
        currency_from: str,
        currency_to: str,
        amount: Decimal,
        cache_max_seconds: int | None,
    ) -> ExchangeResult:
        if self.exchange:
            return await self._try_resolve(
                self.get_provider_instance(),
                currency_from,
                currency_to,
                amount,
                cache_max_seconds,
            )

        for provider_name in PROVIDERS_MAP.keys():
            self.exchange = provider_name
            try:
                return await self._try_resolve(
                    self.get_provider_instance(),
                    currency_from,
                    currency_to,
                    amount,
                    cache_max_seconds,
                )
            except PairNotFound:
                log.warning(
                    f"Pair not found for {currency_from}/{currency_to} "
                    f"on {provider_name}"
                )
                continue

        raise PairNotFound(
            f"No valid exchange found for {currency_from}/{currency_to}"
        )

    async def _try_resolve(
        self,
        provider: Binance | Kucoin,
        currency_from: str,
        currency_to: str,
        amount: Decimal,
        cache_max_seconds: int | None,
    ) -> ExchangeResult:
        try:
            return await provider.exchange(
                amount,
                currency_from,
                currency_to,
                cache_max_seconds,
            )
        except PairNotFound:
            log.info(
                f"Pair not found for {currency_from}/{currency_to}. "
                f"Trying intermediaries..."
            )
            return await self._resolve_via_intermediary(
                provider,
                currency_from,
                currency_to,
                amount,
                cache_max_seconds,
            )

    async def _resolve_via_intermediary(
        self,
        provider: Binance | Kucoin,
        currency_from: str,
        currency_to: str,
        amount: Decimal,
        cache_max_seconds: int | None,
    ) -> ExchangeResult:
        for intermediary in INTERMEDIARY_CURRENCIES:
            try:
                intermediate_result = await provider.exchange(
                    amount,
                    currency_from,
                    intermediary,
                    cache_max_seconds,
                )
                result = await provider.exchange(
                    Decimal(intermediate_result.result),
                    intermediary,
                    currency_to,
                    cache_max_seconds,
                )
                result.rate = format_decimal(
                    Decimal(intermediate_result.result)
                    * Decimal(result.rate)
                    / amount
                )
                return result
            except PairNotFound:
                log.warning(
                    f"Intermediary {intermediary} failed "
                    f"for {currency_from}/{currency_to}."
                )
                continue

        raise PairNotFound(
            f"Could not resolve {currency_from}/{currency_to} "
            f"via intermediaries."
        )
