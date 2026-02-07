from sqlalchemy.orm import Session
from src.models.db_models import Listing

DUMMY_LISTINGS = [
    {"title": "MacBook Pro 2019", "description": "16-inch, good condition. Includes charger.", "price": 850, "category": "electronics"},
    {"title": "IKEA Desk", "description": "Pickup only. Lightly used, sturdy.", "price": 60, "category": "furniture"},
    {"title": "Nintendo Switch", "description": "Includes dock + 2 joycons + HDMI cable.", "price": 180, "category": "electronics"},
    {"title": "AirPods Pro (1st Gen)", "description": "Works great, includes case. Sanitized.", "price": 90, "category": "electronics"},
    {"title": "Gaming Chair", "description": "Ergonomic chair, minor wear on armrests.", "price": 75, "category": "furniture"},
    {"title": "Mountain Bike", "description": "Hardtail bike, tuned recently. Helmet optional.", "price": 220, "category": "sports"},
    {"title": "Instant Pot 6qt", "description": "Barely used. Includes sealing ring + accessories.", "price": 55, "category": "home"},
    {"title": "iPhone 12 (64GB)", "description": "Unlocked. Battery health 86%. Small scratch on screen.", "price": 300, "category": "electronics"},
    {"title": "Mechanical Keyboard", "description": "Hot-swappable. Linear switches. RGB.", "price": 65, "category": "electronics"},
    {"title": "Textbook Bundle (CS)", "description": "Algorithms + ML intro books. Great condition.", "price": 40, "category": "books"},
]

def seed_listings(db: Session):
    if db.query(Listing).first():
        return
    db.add_all(Listing(**x) for x in DUMMY_LISTINGS)
    db.commit()