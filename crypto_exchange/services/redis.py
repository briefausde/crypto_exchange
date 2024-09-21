import redis.asyncio as aioredis
from aiohttp import web
import logging
from typing import AsyncGenerator

log = logging.getLogger(__name__)


async def setup_redis(app: web.Application) -> AsyncGenerator:
    host = app['config'].redis_host
    port = app['config'].redis_port

    redis = aioredis.Redis(host=host, port=port, db=0)

    app["redis"] = redis

    log.info(f"Redis configured. {host}:{port}")

    try:
        yield redis
    finally:
        await redis.close()
        log.info('Redis connection closed.')
