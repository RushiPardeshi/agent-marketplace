from pydantic import BaseModel, Field
from typing import List, Optional

class Product(BaseModel):
    name: str
    description: Optional[str] = None
    listing_price: float = Field(..., gt=0)

from enum import Enum

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