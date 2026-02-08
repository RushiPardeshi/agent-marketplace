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
    {"title": "MacBook Air 2020 (M1)", "description": "13-inch, 8GB RAM, 256GB SSD. Great battery. Includes charger.", "price": 650, "category": "electronics"},
    {"title": "MacBook Pro 2021 (14-inch)", "description": "M1 Pro, 16GB RAM, 512GB SSD. Excellent condition.", "price": 1200, "category": "electronics"},
    {"title": "Dell XPS 13 (9310)", "description": "i7, 16GB RAM, 512GB SSD. 13-inch. Light scratches.", "price": 720, "category": "electronics"},
    {"title": "Lenovo ThinkPad T480", "description": "i5, 16GB RAM, 512GB SSD. Great keyboard. New battery.", "price": 420, "category": "electronics"},
    {"title": "HP Spectre x360", "description": "2-in-1 touchscreen, 16GB RAM, 512GB SSD. Includes pen.", "price": 680, "category": "electronics"},
    {"title": "ASUS ROG Gaming Laptop", "description": "RTX 3060, 16GB RAM, 1TB SSD. 144Hz display. Runs cool.", "price": 950, "category": "electronics"},
    {"title": "Acer Nitro 5 Gaming Laptop", "description": "GTX 1650, 16GB RAM, 512GB SSD. Great starter gaming.", "price": 550, "category": "electronics"},
    {"title": "MSI Stealth 15", "description": "RTX 3070, 32GB RAM, 1TB SSD. Thin and powerful.", "price": 1250, "category": "electronics"},
    {"title": "Razer Blade 15", "description": "RTX 2070, 16GB RAM, 512GB SSD. Premium build.", "price": 900, "category": "electronics"},
    {"title": "Surface Laptop 4", "description": "13.5-inch, Ryzen 5, 16GB RAM, 512GB SSD. Clean.", "price": 700, "category": "electronics"},
    {"title": "iPhone 11 (128GB)", "description": "Unlocked. Battery health 83%. Includes case.", "price": 220, "category": "electronics"},
    {"title": "iPhone 11 Pro (64GB)", "description": "Unlocked. Battery health 86%. Minor wear.", "price": 260, "category": "electronics"},
    {"title": "iPhone 12 Mini (128GB)", "description": "Unlocked. Battery health 88%. Great compact phone.", "price": 260, "category": "electronics"},
    {"title": "iPhone 12 (128GB)", "description": "Unlocked. Battery health 90%. Screen protector on.", "price": 340, "category": "electronics"},
    {"title": "iPhone 13 (128GB)", "description": "Unlocked. Battery health 92%. Like new.", "price": 420, "category": "electronics"},
    {"title": "iPhone 13 Pro (256GB)", "description": "Unlocked. Battery health 90%. ProMotion display.", "price": 520, "category": "electronics"},
    {"title": "iPhone 14 (128GB)", "description": "Unlocked. Battery health 95%. Includes box.", "price": 560, "category": "electronics"},
    {"title": "iPhone 14 Pro (128GB)", "description": "Unlocked. Battery health 93%. Always in case.", "price": 720, "category": "electronics"},
    {"title": "iPhone SE (2022) (64GB)", "description": "Unlocked. Battery health 91%. Touch ID.", "price": 190, "category": "electronics"},
    {"title": "iPhone XR (64GB)", "description": "Unlocked. Battery health 80%. Good condition.", "price": 150, "category": "electronics"},
    {"title": "Samsung Galaxy S21", "description": "Unlocked. 128GB. Great camera. Minor scratches.", "price": 260, "category": "electronics"},
    {"title": "Google Pixel 7", "description": "Unlocked. 128GB. Great photos. Includes case.", "price": 320, "category": "electronics"},
    {"title": "Sony WH-1000XM4 Headphones", "description": "Noise-cancelling. Includes case and cable.", "price": 160, "category": "electronics"},
    {"title": "iPad Air 4 (64GB)", "description": "Wi-Fi. Includes charger. Great for notes.", "price": 320, "category": "electronics"},
    {"title": "iPad Pro 11-inch (2020)", "description": "128GB Wi-Fi. Includes case. Smooth performance.", "price": 520, "category": "electronics"},
    {"title": "Kindle Paperwhite", "description": "Latest gen. Great condition.", "price": 80, "category": "electronics"},
    {"title": "Canon EOS M50 Camera", "description": "Includes kit lens + battery + charger.", "price": 350, "category": "electronics"},
    {"title": "Standing Desk Converter", "description": "Fits 27-inch monitor. Smooth lift.", "price": 70, "category": "furniture"},
    {"title": "Office Monitor 27-inch", "description": "1080p IPS. Includes HDMI cable.", "price": 90, "category": "electronics"},
    {"title": "Air Fryer", "description": "5qt. Clean. Works perfectly.", "price": 45, "category": "home"},
    {"title": "Office Chair", "description": "Ergonomic office chair with adjustable height. Minor wear.", "price": 100, "category": "furniture"},
    {"title": "Dining Table", "description": "Wooden dining table for 6 people. Solid construction.", "price": 200, "category": "furniture"},
    {"title": "Samsung Galaxy S22", "description": "128GB, unlocked. Great camera and performance.", "price": 400, "category": "electronics"},
    {"title": "Dell Inspiron Laptop", "description": "15-inch, i5, 8GB RAM, 256GB SSD. Good for everyday use.", "price": 500, "category": "electronics"},
    {"title": "Recliner Chair", "description": "Comfortable recliner with footrest. Leather upholstery.", "price": 150, "category": "furniture"},
    {"title": "Coffee Table", "description": "Modern glass coffee table. Includes storage.", "price": 80, "category": "furniture"},
    {"title": "Google Pixel 6", "description": "128GB, unlocked. Excellent photo quality.", "price": 250, "category": "electronics"},
    {"title": "HP Pavilion Laptop", "description": "14-inch, Ryzen 5, 16GB RAM, 512GB SSD.", "price": 600, "category": "electronics"},
    {"title": "Set of 4 Bar Stools", "description": "Metal bar stools with backrest. Height adjustable.", "price": 200, "category": "furniture"},
    {"title": "End Table", "description": "Small wooden end table. Perfect for living room.", "price": 60, "category": "furniture"},
    {"title": "OnePlus 9", "description": "128GB, unlocked. Fast charging and smooth UI.", "price": 300, "category": "electronics"},
    {"title": "Acer Aspire Laptop", "description": "15.6-inch, i3, 8GB RAM, 512GB SSD. Budget friendly.", "price": 450, "category": "electronics"},
    {"title": "Armchair", "description": "Plush armchair with ottoman. Cozy for reading.", "price": 120, "category": "furniture"},
    {"title": "Console Table", "description": "Narrow console table for entryway. Sleek design.", "price": 100, "category": "furniture"},
    {"title": "Motorola Edge Phone", "description": "128GB, unlocked. Curved screen and good battery.", "price": 350, "category": "electronics"},
    {"title": "Lenovo IdeaPad Laptop", "description": "13-inch, i5, 8GB RAM, 256GB SSD. Portable.", "price": 550, "category": "electronics"},
    {"title": "Set of 6 Dining Chairs", "description": "Wooden dining chairs. Matching set.", "price": 300, "category": "furniture"},
    {"title": "Side Table", "description": "Round side table with drawer. Versatile.", "price": 40, "category": "furniture"},
    {"title": "Nokia 8.3 Phone", "description": "64GB, unlocked. Reliable and affordable.", "price": 200, "category": "electronics"},
    {"title": "ASUS VivoBook Laptop", "description": "15.6-inch, Ryzen 7, 16GB RAM, 512GB SSD.", "price": 480, "category": "electronics"},
    {"title": "Rocking Chair", "description": "Traditional rocking chair. Great for nursery.", "price": 90, "category": "furniture"},
    {"title": "Picnic Table", "description": "Outdoor picnic table. Seats 4. Weather resistant.", "price": 150, "category": "furniture"},
    {"title": "Xiaomi Mi 11 Phone", "description": "128GB, unlocked. High-end specs at good price.", "price": 280, "category": "electronics"},
    {"title": "MSI Modern Laptop", "description": "14-inch, i7, 16GB RAM, 512GB SSD. Business style.", "price": 650, "category": "electronics"},
    {"title": "Set of 2 Folding Chairs", "description": "Lightweight folding chairs. Easy storage.", "price": 60, "category": "furniture"},
    {"title": "Workbench", "description": "Heavy-duty workbench for garage. Sturdy.", "price": 200, "category": "furniture"},
    {"title": "Sony Xperia Phone", "description": "128GB, unlocked. Waterproof and durable.", "price": 320, "category": "electronics"},
    {"title": "Razer Book Laptop", "description": "13-inch, i7, 16GB RAM, 512GB SSD. Ultra-thin.", "price": 1000, "category": "electronics"},
    {"title": "Bean Bag Chair", "description": "Large bean bag chair. Comfortable for gaming.", "price": 80, "category": "furniture"},
    {"title": "Patio Table", "description": "Outdoor patio table. Seats 4. Aluminum frame.", "price": 120, "category": "furniture"},
]


def seed_listings(db: Session):
    # Remove bogus placeholder rows created during manual Swagger testing
    db.query(Listing).filter(
        Listing.title == "string",
        Listing.price == 0,
    ).delete(synchronize_session=False)
    db.commit()

    # Seed any missing dummy listings (idempotent)
    existing_titles = {t for (t,) in db.query(Listing.title).all() if t}

    to_add = []
    for item in DUMMY_LISTINGS:
        if item["title"] not in existing_titles:
            item["seller_min_price"] = float(item["price"]) * 0.8
            to_add.append(Listing(**item))

    if to_add:
        db.add_all(to_add)
        db.commit()