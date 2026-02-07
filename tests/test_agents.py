import pytest
from unittest.mock import patch
from src.agents.seller import SellerAgent
from src.agents.buyer import BuyerAgent

def test_seller_agent_prompt():
    agent = SellerAgent(min_price=900)
    prompt = agent.build_prompt("context", 950, rounds_left=5, market_context="High demand")
    assert "minimum acceptable price is $900" in prompt
    assert "context" in prompt
    assert "last offer from the buyer was $950" in prompt
    assert "You have 5 rounds" in prompt
    assert "High demand" in prompt
    assert "Closing Logic" in prompt # New explicit logic

def test_buyer_agent_prompt():
    agent = BuyerAgent(max_price=1200)
    prompt = agent.build_prompt("context", 1100, rounds_left=2, market_context="High supply")
    assert "maximum budget is $1200" in prompt
    assert "context" in prompt
    assert "last offer from the seller was $1100" in prompt
    assert "You have 2 rounds" in prompt
    assert "running out of patience" in prompt
    assert "High supply" in prompt
    assert "Closing Logic" in prompt # New explicit logic

@patch("src.agents.base.OpenAI")
def test_seller_agent_propose(MockOpenAI):
    # Setup the mock client and its response
    mock_client = MockOpenAI.return_value
    mock_response = type("obj", (), {"choices": [type("obj", (), {"message": type("obj", (), {"content": "{'offer': 950, 'message': 'Best I can do.'}"})})]})
    mock_client.chat.completions.create.return_value = mock_response
    
    agent = SellerAgent(min_price=900)
    # Buyer offered 900. Seller proposes 950. Rationality check passes (950 not < 900).
    result = agent.propose("context", 900, rounds_left=10, market_context="")
    assert result["offer"] == 950
    assert "Best I can do" in result["message"]

@patch("src.agents.base.OpenAI")
def test_seller_agent_enforce_min_price(MockOpenAI):
    # Test safeguard: Model tries to offer 800 (below min 900)
    mock_client = MockOpenAI.return_value
    mock_response = type("obj", (), {"choices": [type("obj", (), {"message": type("obj", (), {"content": "{'offer': 800, 'message': 'Take it or leave it.'}"})})]})
    mock_client.chat.completions.create.return_value = mock_response
    
    agent = SellerAgent(min_price=900)
    # Buyer offered 500. Rationality check passes (800 not < 500). Min price check catches it.
    result = agent.propose("context", 500, rounds_left=1, market_context="")
    assert result["offer"] == 900 # Should be clamped to min
    assert "cannot go lower" in result["message"]

@patch("src.agents.base.OpenAI")
def test_seller_agent_rationality_check(MockOpenAI):
    # Test safeguard: Model tries to offer 950, but Buyer already offered 1000.
    mock_client = MockOpenAI.return_value
    mock_response = type("obj", (), {"choices": [type("obj", (), {"message": type("obj", (), {"content": "{'offer': 950, 'message': 'I am generous.'}"})})]})
    mock_client.chat.completions.create.return_value = mock_response
    
    agent = SellerAgent(min_price=900)
    result = agent.propose("context", 1000, rounds_left=5, market_context="")
    assert result["offer"] == 1000 # Should be corrected to match buyer's higher offer
    assert "I accept your offer" in result["message"]

@patch("src.agents.base.OpenAI")
def test_buyer_agent_propose(MockOpenAI):
    # Setup the mock client and its response
    mock_client = MockOpenAI.return_value
    mock_response = type("obj", (), {"choices": [type("obj", (), {"message": type("obj", (), {"content": "{'offer': 1000, 'message': 'My final offer.'}"})})]})
    mock_client.chat.completions.create.return_value = mock_response
    
    agent = BuyerAgent(max_price=1200)
    # Seller offered 1100. Buyer proposes 1000. Rationality check passes (1000 not > 1100).
    result = agent.propose("context", 1100, rounds_left=10, market_context="")
    assert result["offer"] == 1000
    assert "final offer" in result["message"]

@patch("src.agents.base.OpenAI")
def test_buyer_agent_enforce_max_price(MockOpenAI):
    # Test safeguard: Model tries to offer 1300 (above max 1200)
    mock_client = MockOpenAI.return_value
    mock_response = type("obj", (), {"choices": [type("obj", (), {"message": type("obj", (), {"content": "{'offer': 1300, 'message': 'Take my money.'}"})})]})
    mock_client.chat.completions.create.return_value = mock_response
    
    agent = BuyerAgent(max_price=1200)
    # Seller offered 1500. Rationality check passes (1300 not > 1500). Max price check catches it.
    result = agent.propose("context", 1500, rounds_left=1, market_context="")
    assert result["offer"] == 1200 # Should be clamped to max
    assert "cannot go higher" in result["message"]

@patch("src.agents.base.OpenAI")
def test_buyer_agent_rationality_check(MockOpenAI):
    # Test safeguard: Model tries to offer 1100, but Seller already offered 1000.
    mock_client = MockOpenAI.return_value
    mock_response = type("obj", (), {"choices": [type("obj", (), {"message": type("obj", (), {"content": "{'offer': 1100, 'message': 'Take it.'}"})})]})
    mock_client.chat.completions.create.return_value = mock_response
    
    agent = BuyerAgent(max_price=1200)
    result = agent.propose("context", 1000, rounds_left=5, market_context="")
    assert result["offer"] == 1000 # Should be corrected to match seller's lower offer
    assert "I accept your offer" in result["message"]
