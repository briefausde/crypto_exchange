import logging
from decimal import Decimal

from aiohttp import web

from crypto_exchange.api.schemas import ConvertRequest, ConvertResponse
from crypto_exchange.exchange.exceptions import (
    InvalidAssetAmount,
    InvalidProvider,
    PairNotFound,
    ProviderBadResponse,
)
from crypto_exchange.exchange.resolver import ExchangeResolver

logger = logging.getLogger(__name__)


async def convert(request: web.Request) -> web.Response:
    try:
        request_json = await request.json()
        data = ConvertRequest(**request_json)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)

    currency_from = data.currency_from.upper()
    currency_to = data.currency_to.upper()

    resolver = ExchangeResolver(
        http_session=request.app["http_session"],
        redis=request.app["redis"],
        exchange=data.exchange,
    )
    try:
        result = await resolver.resolve(
            currency_from=data.currency_from.upper(),
            currency_to=data.currency_to.upper(),
            amount=Decimal(data.amount),
            cache_max_seconds=data.cache_max_seconds,
        )
    except InvalidProvider as e:
        return web.json_response({"error": str(e)}, status=400)
    except InvalidAssetAmount as e:
        return web.json_response({"error": str(e)}, status=400)
    except ProviderBadResponse:
        return web.json_response(
            {"error": "Error with exchange, please try again later."},
            status=500,
        )
    except PairNotFound as e:
        return web.json_response({"error": str(e)}, status=400)
    except Exception as e:
        logger.exception(e)
        return web.json_response(
            {"error": "Internal error, try later..."}, status=500
        )

    convert_response = ConvertResponse(
        currency_from=currency_from,
        currency_to=currency_to,
        exchange=resolver.exchange,
        **result.dict(),
    )

    return web.json_response(convert_response.dict())
