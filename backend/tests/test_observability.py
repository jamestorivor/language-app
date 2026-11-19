import json
import logging
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.observability import RequestLoggingMiddleware, logger


class CollectRecords(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(json.loads(record.getMessage()))


def test_request_logging_correlates_requests_without_logging_private_data():
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.post("/items/{item_id}")
    async def item(item_id: str):
        return {"ok": True}

    records = CollectRecords()
    logger.addHandler(records)
    try:
        request_id = str(uuid4())
        response = TestClient(app).post(
            "/items/private-item?token=private-token",
            json={"text": "private transcript"},
            headers={"X-Request-ID": request_id},
        )
    finally:
        logger.removeHandler(records)

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id
    assert records.records[-1]["request_id"] == request_id
    assert records.records[-1]["route"] == "/items/{item_id}"
    assert records.records[-1]["status"] == 200
    assert "private" not in json.dumps(records.records)


def test_request_logging_reports_failures_without_exception_messages():
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/fail")
    async def fail():
        raise ValueError("private database password")

    records = CollectRecords()
    logger.addHandler(records)
    try:
        response = TestClient(app, raise_server_exceptions=False).get(
            "/fail", headers={"X-Request-ID": "invalid\nprivate"}
        )
    finally:
        logger.removeHandler(records)

    assert response.status_code == 500
    assert records.records[-1]["event"] == "request_failed"
    assert records.records[-1]["error_type"] == "ValueError"
    assert records.records[-1]["request_id"]
    assert "private" not in json.dumps(records.records)


def test_allowed_browser_origin_receives_cors_headers_for_backend_errors():
    from app.db.session import get_db
    from app.main import app

    def broken_database():
        raise RuntimeError("private database detail")

    app.dependency_overrides[get_db] = broken_database
    try:
        client = TestClient(app, raise_server_exceptions=False)
        preflight = client.options("/api/study/cards", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "x-request-id",
        })
        response = client.get("/api/study/cards?due_only=true", headers={
            "Origin": "http://localhost:5173",
        })
        blocked = client.get("/api/study/cards", headers={"Origin": "https://untrusted.example"})
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.status_code == 500
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["x-request-id"]
    assert response.json() == {"detail": "Internal Server Error"}
    assert "access-control-allow-origin" not in blocked.headers
