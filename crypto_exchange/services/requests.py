import logging
from typing import AsyncGenerator

from aiohttp import ClientSession, ClientTimeout, web

logger = logging.getLogger(__name__)


async def setup_requests(app: web.Application) -> AsyncGenerator:
    session_timeout = ClientTimeout(
        total=None,
        sock_connect=2,
        sock_read=2,
    )
    http_session = ClientSession(timeout=session_timeout)

    app["http_session"] = http_session

    logger.info(f"HTTP session configured.")

    try:
        yield http_session
    finally:
        await http_session.close()
        logger.info("HTTP session closed.")
