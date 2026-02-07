from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from src.models.schemas import NegotiationRequest, NegotiationResult, ListingCreate, ListingOut
from src.services.negotiation import NegotiationService
from sqlalchemy.orm import Session
from src.db import Base, engine, get_db, SessionLocal
from src.models.db_models import Listing
from src.seed import seed_listings
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