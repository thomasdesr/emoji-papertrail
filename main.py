import secrets
import time
from typing import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from slack_bolt.adapter.fastapi import SlackRequestHandler
import structlog

from config import config
from slack_app import slack_app

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

# Setup FastAPI & have it serve the Slack app
app = FastAPI()
slack_app_handler = SlackRequestHandler(slack_app)

@app.middleware("http")
async def request_id(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = request.headers.get(
        config.request_id_http_header,
        f"local:{secrets.token_urlsafe()}",
    )

    request.state.request_id = request_id
    return await call_next(request)


@app.middleware("http")
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


@app.post("/slack/events")
async def handle_slack_event(request: Request) -> Response:
    return await slack_app_handler.handle(request)
