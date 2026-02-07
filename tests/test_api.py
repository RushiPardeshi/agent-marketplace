import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from src.main import app

client = TestClient(app)

@patch("src.services.negotiation.NegotiationService.negotiate")
def test_negotiate_endpoint_success(mock_negotiate):
    mock_negotiate.return_value = {
        "agreed": True,
        "final_price": 950,
        "turns": [],
        "reason": "Agreement"
    }
    payload = {
        "product": {"name": "Laptop", "listing_price": 1200},
        "seller_min_price": 900,
        "buyer_max_price": 1000,
        "active_competitor_sellers": 1,
        "active_interested_buyers": 5
    }
    response = client.post("/negotiate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["agreed"] is True
    assert data["final_price"] == 950

@patch("src.services.negotiation.NegotiationService.negotiate")
def test_negotiate_endpoint_failure(mock_negotiate):
    mock_negotiate.side_effect = Exception("Negotiation error")
    payload = {
        "product": {"name": "Laptop", "listing_price": 1200},
        "seller_min_price": 900,
        "buyer_max_price": 1000,
        "active_competitor_sellers": 1,
        "active_interested_buyers": 5
    }
    response = client.post("/negotiate", json=payload)
    assert response.status_code == 500
    assert "Negotiation error" in response.text
