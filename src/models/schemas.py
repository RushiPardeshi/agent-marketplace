from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional

class Product(BaseModel):
    name: str
    description: Optional[str] = None
    listing_price: float = Field(..., gt=0)

class NegotiationRequest(BaseModel):
    product: Product
    seller_min_price: float = Field(..., gt=0)
    buyer_max_price: float = Field(..., gt=0)
    
    # Market Context (Supply & Demand)
    active_competitor_sellers: int = Field(0, ge=0, description="Number of other sellers selling this item")
    active_interested_buyers: int = Field(0, ge=0, description="Number of other buyers interested in this item")
    
    initial_seller_offer: Optional[float] = None
    initial_buyer_offer: Optional[float] = None
    initial_seller_message: Optional[str] = None
    initial_buyer_message: Optional[str] = None
    
    # Deprecated/Optional (for backward compatibility or override)
    seller_patience: Optional[int] = Field(None, description="Explicit round limit override")
    buyer_patience: Optional[int] = Field(None, description="Explicit round limit override")

    model_config = ConfigDict(
        json_schema_extra={
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
    )

class ListingNegotiationRequest(BaseModel):
    seller_min_price: Optional[float] = Field(None, gt=0)
    buyer_max_price: float = Field(..., gt=0)

    # Market Context (Supply & Demand)
    active_competitor_sellers: int = Field(0, ge=0, description="Number of other sellers selling this item")
    active_interested_buyers: int = Field(0, ge=0, description="Number of other buyers interested in this item")

    initial_seller_offer: Optional[float] = None
    initial_buyer_offer: Optional[float] = None
    initial_seller_message: Optional[str] = None
    initial_buyer_message: Optional[str] = None

    seller_patience: Optional[int] = Field(None, description="Explicit round limit override")
    buyer_patience: Optional[int] = Field(None, description="Explicit round limit override")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "buyer_max_price": 900,
                "active_competitor_sellers": 1,
                "active_interested_buyers": 2,
                "initial_seller_offer": None,
                "initial_buyer_offer": None,
                "initial_seller_message": None,
                "initial_buyer_message": None,
                "seller_patience": None,
                "buyer_patience": None,
            }
        }
    )

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
    seller_min_price: float | None = None

class ListingOut(BaseModel):
    id: int
    title: str
    description: str | None = None
    price: float
    category: str | None = None

    model_config = ConfigDict(from_attributes=True)

class AIResponse(BaseModel):
    offer: float
    message: str

class SearchRequest(BaseModel):
    query: str = Field(..., description="Natural language query, e.g., 'I want a laptop under $1000 with good battery'")
    user_budget: Optional[float] = Field(None, gt=0, description="Optional explicit budget override")
    top_k: int = Field(5, ge=1, le=20)
    use_vector: bool = Field(True, description="Use embeddings-based semantic search if available")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "I need a gaming laptop with at least 16GB RAM under $1500",
                "user_budget": 1500.0,
                "top_k": 5,
                "use_vector": True
            }
        }
    )

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

    model_config = ConfigDict(
        json_schema_extra={
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
    )