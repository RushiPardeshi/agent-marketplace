from pydantic import BaseModel, Field
from typing import List, Optional

class Product(BaseModel):
    name: str
    description: Optional[str] = None
    listing_price: float = Field(..., gt=0)

class NegotiationRequest(BaseModel):
    product: Product
    seller_min_price: float = Field(..., gt=0)
    buyer_max_price: float = Field(..., gt=0)
    initial_seller_offer: Optional[float] = None
    initial_buyer_offer: Optional[float] = None

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
