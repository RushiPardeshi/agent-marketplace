import pytest
from unittest.mock import patch
from src.agents.seller import SellerAgent
from src.agents.buyer import BuyerAgent

@patch("src.agents.base.OpenAI")
def test_seller_agent_propose(MockOpenAI):
    # Setup the mock client and its response
    mock_client = MockOpenAI.return_value
    
    # Mock output_parsed object with model_dump
    mock_output = type("obj", (), {})()
    mock_output.model_dump = lambda: {"offer": 950, "message": "Best I can do."}
    
    mock_response = type("obj", (), {"output_parsed": mock_output})
    mock_client.responses.parse.return_value = mock_response
    
    agent = SellerAgent(min_price=900)
    # Buyer offered 900. Seller proposes 950. Rationality check passes (950 not < 900).
    result = agent.propose("context", 900, rounds_left=10, market_context="")
    assert result["offer"] == 950
    assert "Best I can do" in result["message"]

@patch("src.agents.base.OpenAI")
def test_seller_agent_enforce_min_price(MockOpenAI):
    # Test safeguard: Model tries to offer 800 (below min 900)
    mock_client = MockOpenAI.return_value
    
    mock_output = type("obj", (), {})()
    mock_output.model_dump = lambda: {"offer": 800, "message": "Take it or leave it."}
    
    mock_response = type("obj", (), {"output_parsed": mock_output})
    mock_client.responses.parse.return_value = mock_response
    
    agent = SellerAgent(min_price=900)
    # Buyer offered 500. Rationality check passes (800 not < 500). Min price check catches it.
    result = agent.propose("context", 500, rounds_left=1, market_context="")
    assert result["offer"] == 900 # Should be clamped to min
    assert "cannot go any lower" in result["message"]

@patch("src.agents.base.OpenAI")
def test_seller_agent_rationality_check(MockOpenAI):
    # Test safeguard: Model tries to offer 950, but Buyer already offered 1000.
    mock_client = MockOpenAI.return_value
    
    mock_output = type("obj", (), {})()
    mock_output.model_dump = lambda: {"offer": 950, "message": "I am generous."}
    
    mock_response = type("obj", (), {"output_parsed": mock_output})
    mock_client.responses.parse.return_value = mock_response
    
    agent = SellerAgent(min_price=900)
    result = agent.propose("context", 1000, rounds_left=5, market_context="")
    assert result["offer"] == 1000 # Should be corrected to match buyer's higher offer
    assert "Deal. I accept $1000" in result["message"]

@patch("src.agents.base.OpenAI")
def test_buyer_agent_propose(MockOpenAI):
    # Setup the mock client and its response
    mock_client = MockOpenAI.return_value
    
    mock_output = type("obj", (), {})()
    mock_output.model_dump = lambda: {"offer": 1000, "message": "My final offer."}
    
    mock_response = type("obj", (), {"output_parsed": mock_output})
    mock_client.responses.parse.return_value = mock_response
    
    agent = BuyerAgent(max_price=1200)
    # Seller offered 1100. Buyer proposes 1000. Rationality check passes (1000 not > 1100).
    result = agent.propose("context", 1100, rounds_left=10, market_context="")
    assert result["offer"] == 1000
    assert "final offer" in result["message"]

@patch("src.agents.base.OpenAI")
def test_buyer_agent_enforce_max_price(MockOpenAI):
    # Test safeguard: Model tries to offer 1300 (above max 1200)
    mock_client = MockOpenAI.return_value
    
    mock_output = type("obj", (), {})()
    mock_output.model_dump = lambda: {"offer": 1300, "message": "Take my money."}
    
    mock_response = type("obj", (), {"output_parsed": mock_output})
    mock_client.responses.parse.return_value = mock_response
    
    agent = BuyerAgent(max_price=1200)
    # Seller offered 1500. Rationality check passes (1300 not > 1500). Max price check catches it.
    result = agent.propose("context", 1500, rounds_left=1, market_context="")
    assert result["offer"] == 1200 # Should be clamped to max
    assert "best offer" in result["message"].lower()

@patch("src.agents.base.OpenAI")
def test_buyer_agent_rationality_check(MockOpenAI):
    # Test safeguard: Model tries to offer 1100, but Seller already offered 1000.
    mock_client = MockOpenAI.return_value
    
    mock_output = type("obj", (), {})()
    mock_output.model_dump = lambda: {"offer": 1100, "message": "Take it."}
    
    mock_response = type("obj", (), {"output_parsed": mock_output})
    mock_client.responses.parse.return_value = mock_response
    
    agent = BuyerAgent(max_price=1200)
    result = agent.propose("context", 1000, rounds_left=5, market_context="")
    assert result["offer"] == 1000 # Should be corrected to match seller's lower offer
    assert "Deal. I accept $1000" in result["message"]

@patch("src.agents.base.OpenAI")
def test_buyer_message_sanitization(MockOpenAI):
    mock_client = MockOpenAI.return_value
    
    mock_output = type("obj", (), {})()
    mock_output.model_dump = lambda: {"offer": 1100, "message": "I can only go as high as $1200."}
    
    mock_response = type("obj", (), {"output_parsed": mock_output})
    mock_client.responses.parse.return_value = mock_response
    
    agent = BuyerAgent(max_price=1200)
    result = agent.propose("context", 1150, rounds_left=5, market_context="")
    assert "best offer" in result["message"]
    assert "1200" not in result["message"]

@patch("src.agents.base.OpenAI")
def test_seller_message_sanitization(MockOpenAI):
    mock_client = MockOpenAI.return_value
    
    mock_output = type("obj", (), {})()
    mock_output.model_dump = lambda: {"offer": 950, "message": "This is my minimum."}
    
    mock_response = type("obj", (), {"output_parsed": mock_output})
    mock_client.responses.parse.return_value = mock_response
    
    agent = SellerAgent(min_price=900)
    result = agent.propose("context", 900, rounds_left=5, market_context="")
    assert "as low as I can go" in result["message"]
    assert "minimum" not in result["message"]

@patch("src.agents.base.OpenAI")
def test_seller_monotonic_price_safeguard(MockOpenAI):
    # Test safeguard: Seller tries to increase their offer from previous round
    mock_client = MockOpenAI.return_value
    
    mock_output = type("obj", (), {})()
    mock_output.model_dump = lambda: {"offer": 1050, "message": "Actually, I want more."}
    
    mock_response = type("obj", (), {"output_parsed": mock_output})
    mock_client.responses.parse.return_value = mock_response
    
    agent = SellerAgent(min_price=900)
    # Context shows seller previously offered 1000
    context = "Buyer offers $950: I can do this.\nSeller offers $1000: Best price."
    result = agent.propose(context, 950, rounds_left=5, market_context="")
    
    # Should be clamped to previous seller offer
    assert result["offer"] == 1000
    assert "holding firm at $1000" in result["message"]

@patch("src.agents.base.OpenAI")
def test_seller_monotonic_price_with_correction(MockOpenAI):
    # Test safeguard: Seller tries to increase from a corrected offer
    mock_client = MockOpenAI.return_value
    
    mock_output = type("obj", (), {})()
    mock_output.model_dump = lambda: {"offer": 1100, "message": "I need more."}
    
    mock_response = type("obj", (), {"output_parsed": mock_output})
    mock_client.responses.parse.return_value = mock_response
    
    agent = SellerAgent(min_price=900)
    # Context shows seller offer was corrected to 1050
    context = "Buyer offers $900: Starting low.\nSeller offers $950: My price. (Corrected to $1050)"
    result = agent.propose(context, 900, rounds_left=5, market_context="")
    
    # Should be clamped to the corrected offer (1050), not the original (950)
    assert result["offer"] == 1050
    assert "holding firm at $1050" in result["message"]
