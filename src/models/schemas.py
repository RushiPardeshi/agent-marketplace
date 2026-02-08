from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum

class Product(BaseModel):
    name: str
    description: Optional[str] = None
    listing_price: float = Field(..., gt=0)

class MarketBehavior(str, Enum):
    AGGRESSIVE = "aggressive"  # Wants deal fast / High demand
    PATIENT = "patient"       # Willing to wait / Low demand
    BALANCED = "balanced"     # Normal

class NegotiationRequest(BaseModel):
    product: Product
    seller_min_price: float = Field(..., gt=0)
    buyer_max_price: float = Field(..., gt=0)
    
    # Market Context (Supply & Demand)
    active_competitor_sellers: int = Field(0, ge=0, description="Number of other sellers selling this item")
    active_interested_buyers: int = Field(0, ge=0, description="Number of other buyers interested in this item")
    
    initial_seller_offer: Optional[float] = None
    initial_buyer_offer: Optional[float] = None
    
    # Deprecated/Optional (for backward compatibility or override)
    seller_patience: Optional[int] = Field(None, description="Explicit round limit override")
    buyer_patience: Optional[int] = Field(None, description="Explicit round limit override")

    class Config:
        schema_extra = {
            "example": {
                "product": {
                    "name": "Laptop",
                    "description": "Lightly used, includes charger",
                    "listing_price": 1200,
                },
                "seller_min_price": 900,
                "buyer_max_price": 1100,
                "active_competitor_sellers": 1,
                "active_interested_buyers": 5,
                "initial_seller_offer": None,
                "initial_buyer_offer": None,
                "seller_patience": None,
                "buyer_patience": None,
            }
        }

class ListingNegotiationRequest(BaseModel):
    seller_min_price: float = Field(..., gt=0)
    buyer_max_price: float = Field(..., gt=0)

    # Market Context (Supply & Demand)
    active_competitor_sellers: int = Field(0, ge=0, description="Number of other sellers selling this item")
    active_interested_buyers: int = Field(0, ge=0, description="Number of other buyers interested in this item")

    initial_seller_offer: Optional[float] = None
    initial_buyer_offer: Optional[float] = None

    seller_patience: Optional[int] = Field(None, description="Explicit round limit override")
    buyer_patience: Optional[int] = Field(None, description="Explicit round limit override")

    class Config:
        schema_extra = {
            "example": {
                "seller_min_price": 700,
                "buyer_max_price": 900,
                "active_competitor_sellers": 1,
                "active_interested_buyers": 2,
                "initial_seller_offer": None,
                "initial_buyer_offer": None,
                "seller_patience": None,
                "buyer_patience": None,
            }
        }

class NegotiationTurn(BaseModel):
    round: int
    agent: str  # 'seller' or 'buyer'
    offer: float
    message: str

class NegotiationResult(BaseModel):
    agreed: bool
    final_price: Optional[float] = None
    turns: List[NegotiationTurn]
    reason: Optional[str] = None
    
class ListingCreate(BaseModel):
    title: str
    description: str | None = None
    price: float
    category: str | None = None

class ListingOut(ListingCreate):
    id: int

    class Config:
        from_attributes = True

class AIResponse(BaseModel):
    offer: float
    message: str

# Multi-Agent Negotiation Models

class AgentIdentity(BaseModel):
    agent_id: str  # e.g., "buyer_1", "seller_1"
    role: str  # "buyer" or "seller"

class BuyerConfig(BaseModel):
    agent_id: str
    max_price: float = Field(..., gt=0)
    interested_seller_ids: List[str] = Field(default_factory=list)  # Sellers this buyer wants to negotiate with
    initial_offer: Optional[float] = None
    patience: Optional[int] = None
    active: bool = True  # False once buyer makes a deal

class SellerConfig(BaseModel):
    agent_id: str
    listing_id: int
    min_price: float = Field(..., gt=0)
    listing_price: float = Field(..., gt=0)
    initial_offer: Optional[float] = None
    patience: Optional[int] = None
    active: bool = True  # False once seller makes a deal

class MarketplaceContext(BaseModel):
    """Global marketplace awareness for all agents"""
    total_active_buyers: int = 0
    total_active_sellers: int = 0
    active_negotiations_count: int = 0
    recent_completed_prices: List[float] = Field(default_factory=list)
    
class MultiAgentNegotiationTurn(BaseModel):
    round: int
    negotiation_id: str  # Which specific 1-1 negotiation this belongs to
    agent_id: str  # "buyer_1", "seller_2", etc.
    agent_role: str  # "buyer" or "seller"
    offer: float
    message: str

class NegotiationState(BaseModel):
    negotiation_id: str
    buyer_id: str
    seller_id: str
    buyer_agent: Optional[dict] = None  # Serialized agent state
    seller_agent: Optional[dict] = None
    buyer_patience: int
    seller_patience: int
    buyer_leverage: str = "medium"
    seller_leverage: str = "medium"
    seller_target: float
    turns: List[MultiAgentNegotiationTurn] = Field(default_factory=list)
    last_buyer_offer: Optional[float] = None
    last_seller_offer: Optional[float] = None
    buyer_stall_count: int = 0
    seller_stall_count: int = 0
    status: str = "active"  # "active", "agreed", "deadlocked", "switched"
    agreed: bool = False
    final_price: Optional[float] = None
    reason: Optional[str] = None
    
class MultiAgentSession(BaseModel):
    session_id: str
    listing_ids: List[int]
    buyers: Dict[str, BuyerConfig]  # buyer_id -> config
    sellers: Dict[str, SellerConfig]  # seller_id -> config
    active_negotiations: Dict[str, NegotiationState] = Field(default_factory=dict)  # negotiation_id -> state
    completed_negotiations: List[NegotiationState] = Field(default_factory=list)
    marketplace_context: MarketplaceContext = Field(default_factory=MarketplaceContext)
    created_at: Optional[str] = None

class CreateSessionRequest(BaseModel):
    buyers: List[BuyerConfig]
    sellers: List[SellerConfig]
    
class StartNegotiationRequest(BaseModel):
    buyer_id: str
    seller_id: str

class AutomateSessionRequest(BaseModel):
    """Request to run entire session automatically with agent autonomy"""
    max_rounds_per_negotiation: int = Field(20, description="Max turns per negotiation before giving up")
    allow_agent_switching: bool = Field(True, description="Allow buyer agents to switch sellers autonomously")

class SessionResponse(BaseModel):
    session_id: str
    marketplace_context: MarketplaceContext
    active_negotiations: List[NegotiationState]
    completed_negotiations: List[NegotiationState]

class SearchRequest(BaseModel):
    query: str = Field(..., description="Natural language query, e.g., 'I want a laptop under $1000 with good battery'")
    user_budget: Optional[float] = Field(None, gt=0, description="Optional explicit budget override")
    top_k: int = Field(5, ge=1, le=20)
    use_vector: bool = Field(True, description="Use embeddings-based semantic search if available")

    class Config:
        schema_extra = {
            "example": {
                "query": "I need a gaming laptop with at least 16GB RAM under $1500",
                "user_budget": 1500.0,
                "top_k": 5,
                "use_vector": True
            }
        }

class ParsedQuery(BaseModel):
    product_type: Optional[str] = None          # "laptop"
    description: Optional[str] = None           # "good battery, 16GB"
    max_budget: Optional[float] = None          # extracted or user-provided
    min_budget: Optional[float] = None
    category: Optional[str] = None
    parse_confidence: float = Field(0.0, ge=0.0, le=1.0)  # Confidence in parsing (e.g., 1.0 if all fields extracted, 0.5 if partial)

class SearchResult(BaseModel):
    listing: ListingOut
    relevance_score: float = Field(..., ge=0.0, le=1.0)   # normalized
    reasons: List[str] = Field(default_factory=list)      # e.g. ["Semantic match", "Within budget"]
    negotiation_ready: bool                               # True if listing.price <= parsed.max_budget (or user_budget)

class SearchResponse(BaseModel):
    parsed_query: ParsedQuery
    results: List[SearchResult]
    message: str  # short AI summary like "Top match is iPhone 12 at $300..."

    class Config:
        schema_extra = {
            "example": {
                "parsed_query": {
                    "product_type": "laptop",
                    "description": "gaming, 16GB RAM",
                    "max_budget": 1500.0,
                    "min_budget": None,
                    "category": "electronics",
                    "parse_confidence": 0.9
                },
                "results": [
                    {
                        "listing": {
                            "id": 1,
                            "title": "Gaming Laptop",
                            "description": "High-performance laptop with 16GB RAM",
                            "price": 1200.0,
                            "category": "electronics"
                        },
                        "relevance_score": 0.95,
                        "reasons": ["Semantic match on 'gaming laptop'", "Within budget"],
                        "negotiation_ready": True
                    }
                ],
                "message": "Found 1 great match for your gaming laptop under $1500."
            }
        }