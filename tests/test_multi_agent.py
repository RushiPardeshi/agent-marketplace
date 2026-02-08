"""
Tests for multi-agent negotiation functionality
"""

import pytest
from src.repositories import InMemorySessionRepository
from src.services.multi_agent_negotiation import MultiAgentNegotiationService
from src.models.schemas import (
    CreateSessionRequest,
    BuyerConfig,
    SellerConfig,
    MultiAgentSession
)


def test_repository_create_and_get_session():
    """Test basic repository operations"""
    repo = InMemorySessionRepository()
    
    session = MultiAgentSession(
        session_id="test_123",
        listing_ids=[1],
        buyers={"buyer_1": BuyerConfig(agent_id="buyer_1", max_price=1000)},
        sellers={"seller_1": SellerConfig(agent_id="seller_1", listing_id=1, min_price=800, listing_price=1200)}
    )
    
    # Create
    session_id = repo.create_session(session)
    assert session_id == "test_123"
    
    # Get
    retrieved = repo.get_session(session_id)
    assert retrieved is not None
    assert retrieved.session_id == "test_123"
    assert "buyer_1" in retrieved.buyers
    assert "seller_1" in retrieved.sellers


def test_repository_list_sessions():
    """Test listing all sessions"""
    repo = InMemorySessionRepository()
    
    session1 = MultiAgentSession(
        session_id="test_1",
        listing_ids=[1],
        buyers={"buyer_1": BuyerConfig(agent_id="buyer_1", max_price=1000)},
        sellers={"seller_1": SellerConfig(agent_id="seller_1", listing_id=1, min_price=800, listing_price=1200)}
    )
    
    session2 = MultiAgentSession(
        session_id="test_2",
        listing_ids=[2],
        buyers={"buyer_2": BuyerConfig(agent_id="buyer_2", max_price=1500)},
        sellers={"seller_2": SellerConfig(agent_id="seller_2", listing_id=2, min_price=1000, listing_price=1800)}
    )
    
    repo.create_session(session1)
    repo.create_session(session2)
    
    sessions = repo.list_sessions()
    assert len(sessions) == 2
    assert "test_1" in sessions
    assert "test_2" in sessions


def test_repository_delete_session():
    """Test deleting a session"""
    repo = InMemorySessionRepository()
    
    session = MultiAgentSession(
        session_id="test_123",
        listing_ids=[1],
        buyers={"buyer_1": BuyerConfig(agent_id="buyer_1", max_price=1000)},
        sellers={"seller_1": SellerConfig(agent_id="seller_1", listing_id=1, min_price=800, listing_price=1200)}
    )
    
    repo.create_session(session)
    assert repo.get_session("test_123") is not None
    
    # Delete
    result = repo.delete_session("test_123")
    assert result is True
    assert repo.get_session("test_123") is None
    
    # Try deleting non-existent
    result = repo.delete_session("nonexistent")
    assert result is False


def test_service_create_session():
    """Test creating a multi-agent session"""
    repo = InMemorySessionRepository()
    service = MultiAgentNegotiationService(repo)
    
    request = CreateSessionRequest(
        buyers=[
            BuyerConfig(agent_id="buyer_1", max_price=1000),
            BuyerConfig(agent_id="buyer_2", max_price=1200)
        ],
        sellers=[
            SellerConfig(agent_id="seller_1", listing_id=1, min_price=800, listing_price=1200),
            SellerConfig(agent_id="seller_2", listing_id=2, min_price=900, listing_price=1300)
        ]
    )
    
    session = service.create_session(request)
    
    assert session.session_id is not None
    assert len(session.buyers) == 2
    assert len(session.sellers) == 2
    assert session.marketplace_context.total_active_buyers == 2
    assert session.marketplace_context.total_active_sellers == 2
    assert len(session.active_negotiations) == 0


def test_service_start_negotiation():
    """Test starting a negotiation between buyer and seller"""
    repo = InMemorySessionRepository()
    service = MultiAgentNegotiationService(repo)
    
    request = CreateSessionRequest(
        buyers=[BuyerConfig(agent_id="buyer_1", max_price=1000)],
        sellers=[SellerConfig(agent_id="seller_1", listing_id=1, min_price=800, listing_price=1200)]
    )
    
    session = service.create_session(request)
    
    # Start negotiation
    negotiation = service.start_negotiation(
        session_id=session.session_id,
        buyer_id="buyer_1",
        seller_id="seller_1"
    )
    
    assert negotiation.negotiation_id is not None
    assert negotiation.buyer_id == "buyer_1"
    assert negotiation.seller_id == "seller_1"
    assert negotiation.status == "active"
    assert len(negotiation.turns) == 0
    
    # Check session updated
    updated_session = service.get_session_status(session.session_id)
    assert len(updated_session.active_negotiations) == 1
    assert updated_session.marketplace_context.active_negotiations_count == 1


def test_service_leverage_calculation():
    """Test leverage calculation with different buyer/seller counts"""
    repo = InMemorySessionRepository()
    service = MultiAgentNegotiationService(repo)
    
    # High buyer leverage (many sellers)
    request1 = CreateSessionRequest(
        buyers=[BuyerConfig(agent_id="buyer_1", max_price=1000)],
        sellers=[
            SellerConfig(agent_id=f"seller_{i}", listing_id=i, min_price=800, listing_price=1200)
            for i in range(1, 4)
        ]
    )
    session1 = service.create_session(request1)
    neg1 = service.start_negotiation(session1.session_id, "buyer_1", "seller_1")
    assert neg1.buyer_leverage == "high"
    assert neg1.seller_leverage == "low"
    
    # High seller leverage (many buyers)
    request2 = CreateSessionRequest(
        buyers=[
            BuyerConfig(agent_id=f"buyer_{i}", max_price=1000)
            for i in range(1, 4)
        ],
        sellers=[SellerConfig(agent_id="seller_1", listing_id=1, min_price=800, listing_price=1200)]
    )
    session2 = service.create_session(request2)
    neg2 = service.start_negotiation(session2.session_id, "buyer_1", "seller_1")
    assert neg2.buyer_leverage == "low"
    assert neg2.seller_leverage == "high"


def test_service_prevent_duplicate_negotiation():
    """Test that we can't start duplicate negotiations"""
    repo = InMemorySessionRepository()
    service = MultiAgentNegotiationService(repo)
    
    request = CreateSessionRequest(
        buyers=[BuyerConfig(agent_id="buyer_1", max_price=1000)],
        sellers=[SellerConfig(agent_id="seller_1", listing_id=1, min_price=800, listing_price=1200)]
    )
    
    session = service.create_session(request)
    
    # Start negotiation
    service.start_negotiation(session.session_id, "buyer_1", "seller_1")
    
    # Try to start again - should fail
    with pytest.raises(ValueError, match="already active"):
        service.start_negotiation(session.session_id, "buyer_1", "seller_1")


def test_service_switch_seller():
    """Test buyer switching from one seller to another"""
    repo = InMemorySessionRepository()
    service = MultiAgentNegotiationService(repo)
    
    request = CreateSessionRequest(
        buyers=[BuyerConfig(agent_id="buyer_1", max_price=1000)],
        sellers=[
            SellerConfig(agent_id="seller_1", listing_id=1, min_price=800, listing_price=1200),
            SellerConfig(agent_id="seller_2", listing_id=2, min_price=700, listing_price=1100)
        ]
    )
    
    session = service.create_session(request)
    
    # Start negotiation with seller_1
    neg1 = service.start_negotiation(session.session_id, "buyer_1", "seller_1")
    assert neg1.status == "active"
    
    # Switch to seller_2
    new_neg_id = service.switch_seller(
        session_id=session.session_id,
        buyer_id="buyer_1",
        current_seller_id="seller_1",
        new_seller_id="seller_2"
    )
    
    # Check old negotiation marked as switched
    session = service.get_session_status(session.session_id)
    old_neg = None
    for completed in session.completed_negotiations:
        if completed.negotiation_id == neg1.negotiation_id:
            old_neg = completed
            break
    
    assert old_neg is not None
    assert old_neg.status == "switched"
    
    # Check new negotiation started
    assert new_neg_id is not None
    assert new_neg_id in session.active_negotiations
    new_neg = session.active_negotiations[new_neg_id]
    assert new_neg.buyer_id == "buyer_1"
    assert new_neg.seller_id == "seller_2"
    assert new_neg.status == "active"


def test_context_building():
    """Test that context strings are built correctly with agent IDs"""
    repo = InMemorySessionRepository()
    service = MultiAgentNegotiationService(repo)
    
    request = CreateSessionRequest(
        buyers=[BuyerConfig(agent_id="buyer_1", max_price=1000)],
        sellers=[SellerConfig(agent_id="seller_1", listing_id=1, min_price=800, listing_price=1200)]
    )
    
    session = service.create_session(request)
    negotiation = service.start_negotiation(session.session_id, "buyer_1", "seller_1")
    
    # Manually add some turns for testing
    from src.models.schemas import MultiAgentNegotiationTurn
    negotiation.turns = [
        MultiAgentNegotiationTurn(
            round=1,
            negotiation_id=negotiation.negotiation_id,
            agent_id="buyer_1",
            agent_role="buyer",
            offer=900,
            message="Starting offer"
        ),
        MultiAgentNegotiationTurn(
            round=2,
            negotiation_id=negotiation.negotiation_id,
            agent_id="seller_1",
            agent_role="seller",
            offer=1100,
            message="Counter offer"
        )
    ]
    
    # Build context from buyer's perspective
    context = service._build_context_string(negotiation.turns, "buyer_1")
    assert "You (buyer) offered $900" in context
    assert "seller_1 (seller) offered $1100" in context
    
    # Build context from seller's perspective
    context = service._build_context_string(negotiation.turns, "seller_1")
    assert "buyer_1 (buyer) offered $900" in context
    assert "You (seller) offered $1100" in context
