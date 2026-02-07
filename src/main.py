from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from src.services.negotiation import NegotiationService
from sqlalchemy.orm import Session
from src.db import Base, engine, get_db, SessionLocal
from src.models.db_models import Listing
from src.seed import seed_listings
from src.models.schemas import (
    NegotiationRequest,
    NegotiationResult,
    ListingCreate,
    ListingOut,
    ListingNegotiationRequest,
    Product,
)
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

negotiation_service = NegotiationService()


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_listings(db)
    finally:
        db.close()

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/negotiate", response_model=NegotiationResult)
def negotiate(request: NegotiationRequest):
    try:
        result = negotiation_service.negotiate(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# New endpoint: Negotiate for a specific listing, ensuring product fields match the listing in DB.
@app.post("/listings/{listing_id}/negotiate", response_model=NegotiationResult)
def negotiate_for_listing(
    listing_id: int,
    request: ListingNegotiationRequest,
    db: Session = Depends(get_db),
):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # Build the Product from DB (source of truth)
    product = Product(
        name=listing.title,
        description=listing.description,
        listing_price=float(listing.price),
    )

    # Build the full NegotiationRequest internally
    full_req = NegotiationRequest(
        product=product,
        seller_min_price=request.seller_min_price,
        buyer_max_price=request.buyer_max_price,
        active_competitor_sellers=request.active_competitor_sellers,
        active_interested_buyers=request.active_interested_buyers,
        initial_seller_offer=request.initial_seller_offer,
        initial_buyer_offer=request.initial_buyer_offer,
        seller_patience=request.seller_patience,
        buyer_patience=request.buyer_patience,
    )

    try:
        return negotiation_service.negotiate(full_req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/listings", response_model=list[ListingOut])
def list_listings(q: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Listing)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Listing.title.ilike(like)) | (Listing.description.ilike(like))
        )
    return query.order_by(Listing.id.desc()).all()

@app.get("/listings/{listing_id}", response_model=ListingOut)
def get_listing(listing_id: int, db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing

@app.post("/listings", response_model=ListingOut)
def create_listing(payload: ListingCreate, db: Session = Depends(get_db)):
    listing = Listing(**payload.model_dump())
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing