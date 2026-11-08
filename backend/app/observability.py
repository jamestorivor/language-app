"""Structured request logs without request bodies, query strings, or credentials."""
import json
import logging
import os
import sys
import time
import traceback
from contextvars import ContextVar
from datetime import datetime, timezone
from uuid import UUID, uuid4

from starlette.middleware.base import BaseHTTPMiddleware

request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)
logger = logging.getLogger("language_app")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
logger.setLevel(getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO))
logger.propagate = False


def log_event(level: int, event: str, **fields) -> None:
    record = {"time": datetime.now(timezone.utc).isoformat(), "level": logging.getLevelName(level),
              "event": event, "request_id": request_id_context.get(), **fields}
    logger.log(level, json.dumps(record, ensure_ascii=False, default=str))


def request_id_from_header(value: str | None) -> str:
    try:
        return str(UUID(value)) if value else str(uuid4())
    except (ValueError, AttributeError):
        return str(uuid4())


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request_id_from_header(request.headers.get("x-request-id"))
        context_token = request_id_context.set(request_id)
        start = time.perf_counter()
        try:
            try:
                response = await call_next(request)
            except Exception as exc:
                # Exception messages may include SQL, connection strings, or user text.
                frames = traceback.extract_tb(exc.__traceback__)
                log_event(logging.ERROR, "request_failed", method=request.method,
                          route=getattr(request.scope.get("route"), "path", "unmatched"),
                          status=500, duration_ms=round((time.perf_counter() - start) * 1000, 1),
                          error_type=type(exc).__name__,
                          frames=[f"{os.path.basename(frame.filename)}:{frame.lineno}:{frame.name}" for frame in frames])
                raise
            response.headers["X-Request-ID"] = request_id
            level = logging.ERROR if response.status_code >= 500 else logging.WARNING if response.status_code >= 400 else logging.INFO
            log_event(level, "request_completed", method=request.method,
                      route=getattr(request.scope.get("route"), "path", "unmatched"),
                      status=response.status_code,
                      duration_ms=round((time.perf_counter() - start) * 1000, 1))
            return response
        finally:
            request_id_context.reset(context_token)
