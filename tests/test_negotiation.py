import pytest
from unittest.mock import patch
from src.models.schemas import Product, NegotiationRequest
from src.services.negotiation import NegotiationService

import os
import json

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '../negotiation_outputs')
os.makedirs(OUTPUT_DIR, exist_ok=True)

def save_output(test_name, result):
    path = os.path.join(OUTPUT_DIR, f'{test_name}.json')
    with open(path, 'w') as f:
        json.dump(result.dict() if hasattr(result, 'dict') else result, f, indent=2)

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
        product=Product(name="Laptop", listing_price=1000), # Lower listing to ensure target <= 950
        seller_min_price=900,
        buyer_max_price=1000,
        initial_seller_offer=1000,
        initial_buyer_offer=950
    )
    service = NegotiationService()
    result = service.negotiate(req)
    assert result.agreed
    assert result.final_price == 950
    assert len(result.turns) <= 5
    save_output("test_negotiation_agreement", result)

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
        product=Product(name="Laptop", listing_price=1500),
        seller_min_price=1200,
        buyer_max_price=800,
        initial_seller_offer=1200,
        initial_buyer_offer=800,
        seller_patience=5,
        buyer_patience=5
    )
    service = NegotiationService()
    result = service.negotiate(req)
    assert not result.agreed
    assert result.final_price is None
    assert "Negotiation ended without agreement" in result.reason
    save_output("test_negotiation_deadlock", result)


# Parameterized tests for permutations
import itertools

@patch("src.agents.seller.SellerAgent.propose")
@patch("src.agents.buyer.BuyerAgent.propose")
@pytest.mark.parametrize("buyer_max,seller_min,listing_price", [
    (1000, 900, 950),
    (1200, 1100, 1150),
    (800, 700, 750),
    (1500, 1200, 1400),
    (950, 950, 950),
    (1000, 1200, 1100),
    (900, 800, 850),
])
def test_negotiation_permutations(mock_buyer, mock_seller, buyer_max, seller_min, listing_price):
    if buyer_max >= seller_min:
        # Success case: Agents converge to seller_min
        # Buyer: 1000 -> Seller: 900 -> Buyer: 900 (Accept)
        mock_buyer.side_effect = [
            {"offer": buyer_max, "message": f"My max is {buyer_max}"},
            {"offer": seller_min, "message": "I accept your price."}
        ]
        mock_seller.side_effect = [
            {"offer": seller_min, "message": f"My min is {seller_min}"}
        ]
    else:
        # Failure case: Agents act stubborn
        # Increase mock count to cover "Patient" scenarios (15+ rounds)
        mock_buyer.side_effect = [{"offer": buyer_max, "message": f"My max is {buyer_max}"}] * 20
        mock_seller.side_effect = [{"offer": seller_min, "message": f"My min is {seller_min}"}] * 20
        
    req = NegotiationRequest(
        product=Product(name="TestProduct", listing_price=listing_price),
        seller_min_price=seller_min,
        buyer_max_price=buyer_max,
        initial_seller_offer=seller_min,
        initial_buyer_offer=buyer_max,
        # Ensure deterministic patience (Balanced/Low Leverage)
        active_competitor_sellers=1, 
        active_interested_buyers=1
    )
    service = NegotiationService()
    result = service.negotiate(req)
    
    # Save output for each permutation
    test_name = f"test_negotiation_perm_{buyer_max}_{seller_min}_{listing_price}"
    save_output(test_name, result)
    
    # Assert agreement only if buyer_max >= seller_min
    if buyer_max >= seller_min:
        assert result.agreed
        assert result.final_price == seller_min
    else:
        assert not result.agreed
        assert result.final_price is None

@patch("src.agents.seller.SellerAgent.propose")
@patch("src.agents.buyer.BuyerAgent.propose")
def test_negotiation_seller_target_enforcement(mock_buyer, mock_seller):
    # Scenario: High Seller Leverage (Target will be high)
    # Listing: 1200, Seller Min: 1000.
    # Leverage "high" -> k=0.85 -> Target = 1000 + (200 * 0.85) = 1170.
    # Buyer offers 1100.
    # Seller Agent (mock) TRIES to accept 1100.
    # Service should INTERCEPT and counter-offer 1170 (or 1101, max of target vs offer+1).

    req = NegotiationRequest(
        product=Product(name="HotItem", listing_price=1200),
        seller_min_price=1000,
        buyer_max_price=1200,
        active_competitor_sellers=0,
        active_interested_buyers=10 # High Seller Leverage
    )

    # Provide enough side effects for a longer negotiation if needed
    # Initial offer is just a setup, subsequent are repeated
    mock_buyer.side_effect = [{"offer": 1100, "message": "1100 is my offer."}] * 20
    
    # Seller tries to accept 1100 (which is < 1170 target)
    mock_seller.side_effect = [{"offer": 1100, "message": "I accept."}] * 20

    service = NegotiationService()

    # We only run enough turns to trigger the interaction
    # The loop condition in service is while patience > 0.
    # We just want to check the first seller turn result.
    # Since we can't easily inspect internal state without modifying code, 
    # we can check the transcript after the negotiation (likely fails or continues).
    # But since mocks run out, we might get an error if we don't provide enough side effects.
    # Let's provide more side effects to be safe.
    
    result = service.negotiate(req)
    
    # Analyze the turns
    # Turn 1: Buyer 1100.
    # Turn 2: Seller *would* have said 1100, but service should override to >= 1170.
    
    seller_turn = result.turns[1]
    assert seller_turn.agent == "seller"
    assert seller_turn.offer >= 1170 
    assert "I can't do that" in seller_turn.message

