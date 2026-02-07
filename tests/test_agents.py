import pytest
from unittest.mock import patch
from src.agents.seller import SellerAgent
from src.agents.buyer import BuyerAgent

def test_seller_agent_prompt():
    agent = SellerAgent(min_price=900)
    prompt = agent.build_prompt("context", 950)
    assert "minimum acceptable price is $900" in prompt
    assert "context" in prompt
    assert "last offer from the buyer was $950" in prompt

def test_buyer_agent_prompt():
    agent = BuyerAgent(max_price=1200)
    prompt = agent.build_prompt("context", 1100)
    assert "maximum budget is $1200" in prompt
    assert "context" in prompt
    assert "last offer from the seller was $1100" in prompt

@patch("src.agents.base.OpenAI")
def test_seller_agent_propose(MockOpenAI):
    # Setup the mock client and its response
    mock_client = MockOpenAI.return_value
    mock_response = type("obj", (), {"choices": [type("obj", (), {"message": type("obj", (), {"content": "{'offer': 950, 'message': 'Best I can do.'}"})})]})
    mock_client.chat.completions.create.return_value = mock_response
    
    agent = SellerAgent(min_price=900)
    result = agent.propose("context", 1000)
    assert result["offer"] == 950
    assert "Best I can do" in result["message"]

@patch("src.agents.base.OpenAI")
def test_seller_agent_enforce_min_price(MockOpenAI):
    # Test safeguard: Model tries to offer 800 (below min 900)
    mock_client = MockOpenAI.return_value
    mock_response = type("obj", (), {"choices": [type("obj", (), {"message": type("obj", (), {"content": "{'offer': 800, 'message': 'Take it or leave it.'}"})})]})
    mock_client.chat.completions.create.return_value = mock_response
    
    agent = SellerAgent(min_price=900)
    result = agent.propose("context", 1000)
    assert result["offer"] == 900 # Should be clamped to min
    assert "cannot go lower" in result["message"]

@patch("src.agents.base.OpenAI")
def test_buyer_agent_propose(MockOpenAI):
    # Setup the mock client and its response
    mock_client = MockOpenAI.return_value
    mock_response = type("obj", (), {"choices": [type("obj", (), {"message": type("obj", (), {"content": "{'offer': 1000, 'message': 'My final offer.'}"})})]})
    mock_client.chat.completions.create.return_value = mock_response
    
    agent = BuyerAgent(max_price=1200)
    result = agent.propose("context", 1100)
    assert result["offer"] == 1000
    assert "final offer" in result["message"]

@patch("src.agents.base.OpenAI")
def test_buyer_agent_enforce_max_price(MockOpenAI):
    # Test safeguard: Model tries to offer 1300 (above max 1200)
    mock_client = MockOpenAI.return_value
    mock_response = type("obj", (), {"choices": [type("obj", (), {"message": type("obj", (), {"content": "{'offer': 1300, 'message': 'Take my money.'}"})})]})
    mock_client.chat.completions.create.return_value = mock_response
    
    agent = BuyerAgent(max_price=1200)
    result = agent.propose("context", 1100)
    assert result["offer"] == 1200 # Should be clamped to max
    assert "cannot go higher" in result["message"]
