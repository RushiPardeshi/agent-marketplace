from types import SimpleNamespace

from src.services.search import SearchService


def test_parse_query_user_budget_override(monkeypatch):
    service = SearchService()

    fake_resp = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"max_budget": 500}'))]
    )
    monkeypatch.setattr(service.client.chat.completions, "create", lambda **_kwargs: fake_resp)

    parsed = service.parse_query("laptop under $700", user_budget=900)
    assert parsed.max_budget == 900.0


def test_parse_query_fallback_budget_extraction(monkeypatch):
    service = SearchService()

    fake_resp = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="not json"))]
    )
    monkeypatch.setattr(service.client.chat.completions, "create", lambda **_kwargs: fake_resp)

    parsed = service.parse_query("phone under $450")
    assert parsed.max_budget == 450.0
