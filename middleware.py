from collections.abc import Awaitable, Callable
import secrets
import time

from fastapi import HTTPException, Request, Response
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from config import server_config

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


def middleware_stack() -> list[Middleware]:
    return [
        Middleware(BaseHTTPMiddleware, dispatch=f)
        for f in (
            return_500_on_exception,
            ready,
            request_id,
            log_requests,
        )
    ]


async def return_500_on_exception(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    try:
        return await call_next(request)
    except Exception as e:
        log = logger.bind(request_id=getattr(request.state, "request_id", None))
        log.exception("exception thrown during request handling")
        raise HTTPException(status_code=500) from e


async def ready(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    if request.url.path == "/ready":
        return Response(status_code=200)

    return await call_next(request)


async def request_id(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = request.headers.get(
        server_config.request_id_http_header,
        f"local:{secrets.token_urlsafe()}",
    )

    request.state.request_id = request_id
    return await call_next(request)


async def log_requests(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    log = logger.bind(
        request_id=request.state.request_id,
        source=(f"{request.client.host}" if request.client else "unknown"),
        host=request.url.hostname,
        path=request.url.path,
        method=request.method,
    )

    log.info("Request: Start")
    start_time = time.monotonic()

    response: Response = await call_next(request)

    process_time = (time.monotonic() - start_time) * 1000

    log.info(
        "Request: Stop",
        status_code=response.status_code,
        process_time=f"{process_time:.2f}ms",
    )

    return response
