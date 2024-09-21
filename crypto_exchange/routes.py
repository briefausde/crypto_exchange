from aiohttp import web
from crypto_exchange.api import v1


def setup_routes(app: web.Application) -> None:
    app.router.add_post('/api/v1/convert', v1.convert)
