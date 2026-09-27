"""Logs estructurados (JSON) y middleware que registra cada request con su request_id."""

import logging
import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

import structlog
from fastapi import Request, Response
from structlog.typing import EventDict, WrappedLogger

from app.core import context

REQUEST_ID_HEADER = "X-Request-ID"


def _add_context(_: WrappedLogger, __: str, event_dict: EventDict) -> EventDict:
    request = context.current()
    if request.request_id is not None:
        event_dict["request_id"] = request.request_id
    if request.user_id is not None:
        event_dict["user_id"] = str(request.user_id)
    return event_dict


def configure_logging(*, json: bool) -> None:
    renderer = (
        structlog.processors.JSONRenderer() if json else structlog.dev.ConsoleRenderer(colors=True)
    )
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _add_context,
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )


async def request_logging_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = request.headers.get(REQUEST_ID_HEADER) or uuid4().hex
    token = context.start_request(request_id)
    request_context = context.current()
    started = time.perf_counter()
    try:
        response = await call_next(request)
    finally:
        context.end_request(token)
    response.headers[REQUEST_ID_HEADER] = request_id
    if request.url.path not in ("/api/health", "/api/health/ready"):
        structlog.get_logger().info(
            "request",
            request_id=request_id,
            user_id=str(request_context.user_id) if request_context.user_id else None,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round((time.perf_counter() - started) * 1000, 1),
        )
    return response
