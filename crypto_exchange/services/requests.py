from aiohttp import web, ClientSession, ClientTimeout
import logging
from typing import AsyncGenerator

log = logging.getLogger(__name__)


async def setup_requests(app: web.Application) -> AsyncGenerator:
    session_timeout = ClientTimeout(
        total=None,
        sock_connect=2,
        sock_read=2,
    )
    http_session = ClientSession(timeout=session_timeout)

    app["http_session"] = http_session

    log.info(f"HTTP session configured.")

    try:
        yield http_session
    finally:
        await http_session.close()
        log.info('HTTP session closed.')
