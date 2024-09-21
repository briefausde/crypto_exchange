import asyncio

from aiohttp import web

from crypto_exchange.config import get_config
from crypto_exchange.routes import setup_routes
from crypto_exchange.services.redis import setup_redis
from crypto_exchange.services.requests import setup_requests


def main():
    config = get_config()
    loop = asyncio.new_event_loop()

    asyncio.set_event_loop(loop)

    app = web.Application()
    app['config'] = config
    app['loop'] = loop

    app.cleanup_ctx.extend([
        setup_redis,
        setup_requests,
    ])

    setup_routes(app)
    
    web.run_app(
        app=app,
        host=config.host,
        port=config.port,
    )


if __name__ == '__main__':
    main()
