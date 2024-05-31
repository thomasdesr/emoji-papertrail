from fastapi import FastAPI, Request, Response
from slack_bolt.adapter.fastapi import SlackRequestHandler
import structlog

from middleware import middleware_stack
from slack_app import slack_app

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


app = FastAPI(middleware=middleware_stack())
slack_request_handler = SlackRequestHandler(slack_app)


@app.post("/slack/events")
async def handle_slack_event(request: Request) -> Response:
    return await slack_request_handler.handle(
        request, addition_context_properties={"request_id": request.state.request_id}
    )
