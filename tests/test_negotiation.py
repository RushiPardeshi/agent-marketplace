import pytest
from unittest.mock import patch
from src.models.schemas import Product, NegotiationRequest
from src.services.negotiation import NegotiationService

@patch("src.agents.seller.SellerAgent.propose")
@patch("src.agents.buyer.BuyerAgent.propose")
def test_negotiation_agreement(mock_buyer, mock_seller):
    # Buyer and seller converge to 950
    mock_buyer.side_effect = [
        {"offer": 950, "message": "I can do 950."}
    ]
    mock_seller.side_effect = [
        {"offer": 950, "message": "I accept 950."}
    ]
    req = NegotiationRequest(
        product=Product(name="Laptop"),
        seller_min_price=900,
        buyer_max_price=1000,
        initial_seller_offer=1000,
        initial_buyer_offer=950
    )
    service = NegotiationService(max_rounds=5)
    result = service.negotiate(req)
    assert result.agreed
    assert result.final_price == 950
    assert len(result.turns) <= 5

@patch("src.agents.seller.SellerAgent.propose")
@patch("src.agents.buyer.BuyerAgent.propose")
def test_negotiation_deadlock(mock_buyer, mock_seller):
    # Buyer and seller never agree
    mock_buyer.side_effect = [
        {"offer": 800, "message": "800 is my max."}
    ] * 5
    mock_seller.side_effect = [
        {"offer": 1200, "message": "1200 is my min."}
    ] * 5
    req = NegotiationRequest(
        product=Product(name="Laptop"),
        seller_min_price=1200,
        buyer_max_price=800,
        initial_seller_offer=1200,
        initial_buyer_offer=800
    )
    service = NegotiationService(max_rounds=5)
    result = service.negotiate(req)
    assert not result.agreed
    assert result.final_price is None
    assert "No agreement" in result.reason
