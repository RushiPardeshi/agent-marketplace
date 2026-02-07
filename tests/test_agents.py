import pytest
from unittest.mock import patch
from src.agents.seller import SellerAgent
from src.agents.buyer import BuyerAgent

def test_seller_agent_prompt():
    agent = SellerAgent(min_price=900)
    prompt = agent.build_prompt("context", 950)
    assert "minimum acceptable price is $900" in prompt
    assert "context" in prompt
    assert "last offer was $950" in prompt

def test_buyer_agent_prompt():
    agent = BuyerAgent(max_price=1200)
    prompt = agent.build_prompt("context", 1100)
    assert "maximum acceptable price is $1200" in prompt
    assert "context" in prompt
    assert "last offer was $1100" in prompt

@patch("openai.ChatCompletion.create")
def test_seller_agent_propose(mock_create):
    mock_create.return_value = type("obj", (), {"choices": [type("obj", (), {"message": {"content": "{'offer': 950, 'message': 'Best I can do.'}"}})]})
    agent = SellerAgent(min_price=900)
    result = agent.propose("context", 1000)
    assert result["offer"] == 950
    assert "Best I can do" in result["message"]

@patch("openai.ChatCompletion.create")
def test_buyer_agent_propose(mock_create):
    mock_create.return_value = type("obj", (), {"choices": [type("obj", (), {"message": {"content": "{'offer': 1000, 'message': 'My final offer.'}"}})]})
    agent = BuyerAgent(max_price=1200)
    result = agent.propose("context", 1100)
    assert result["offer"] == 1000
    assert "final offer" in result["message"]
