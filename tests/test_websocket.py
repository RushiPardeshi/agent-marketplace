import json

from fastapi.testclient import TestClient

from src.main import app
from src.models.schemas import ParsedQuery, SearchResponse


class FakeRedis:
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, _ttl, value):
        self.store[key] = value

    def delete(self, key):
        self.store.pop(key, None)


def _patch_redis(monkeypatch):
    from src import main
    monkeypatch.setattr(main, "redis_client", FakeRedis())


def test_ws_invalid_json(monkeypatch):
    _patch_redis(monkeypatch)
    client = TestClient(app)
    with client.websocket_connect("/ws/chat") as ws:
        ws.receive_json()  # session message
        ws.send_text("not json")
        resp = ws.receive_json()
        assert resp["type"] == "error"
        assert "Invalid JSON" in resp["message"]


def test_ws_unknown_type(monkeypatch):
    _patch_redis(monkeypatch)
    client = TestClient(app)
    with client.websocket_connect("/ws/chat") as ws:
        ws.receive_json()
        ws.send_json({"type": "unknown"})
        resp = ws.receive_json()
        assert resp["type"] == "error"
        assert "Unknown message type" in resp["message"]


def test_ws_rate_limit(monkeypatch):
    _patch_redis(monkeypatch)
    from src import main

    def fake_parse_query(_q, _budget=None):
        return ParsedQuery(
            product_type="laptop",
            description=None,
            max_budget=1000.0,
            min_budget=None,
            category=None,
            parse_confidence=1.0,
        )

    def fake_perform_search(_req, _db):
        return SearchResponse(parsed_query=fake_parse_query("x"), results=[], message="none")

    monkeypatch.setattr(main.search_service, "parse_query", fake_parse_query)
    monkeypatch.setattr(main.search_service, "perform_search", fake_perform_search)
    monkeypatch.setattr(main, "generate_refinement_suggestion", lambda *_args, **_kwargs: "suggest")

    client = TestClient(app)
    with client.websocket_connect("/ws/chat") as ws:
        ws.receive_json()
        for i in range(10):
            ws.send_json({"type": "user_query", "content": f"q{i}"})
            resp = ws.receive_json()
            if resp["type"] == "clarify":
                resp = ws.receive_json()
            assert resp["type"] in {"search_results", "updated_results", "error"}
        ws.send_json({"type": "user_query", "content": "q10"})
        resp = ws.receive_json()
        assert resp["type"] == "error"
        assert "Rate limit exceeded" in resp["message"]
