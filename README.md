# agent-marketplace

## Overview
Proof of Concept: Can a seller AI agent and a buyer AI agent reach an agreement through negotiation? This FastAPI backend simulates automated price negotiation using OpenAI's GPT models.

## Features
- **Smart Agents**: Seller and buyer agents negotiate price for a product, acting as advocates for their respective users.
- **Listing Price**: Negotiations start from a public listing price set by the seller.
- **Realistic Haggling**: Agents negotiate like humans, making concessions and defending their price until they converge on a consensus value.
- **Turn-based**: Fully automated, turn-based negotiation loop limited to a max number of rounds.
- **Testing**: Automated tests with mocked LLM calls for fast, free, deterministic testing.

## Setup
1. Clone the repo and install dependencies:
	```sh
	pip install -r requirements.txt
	```
2. Copy `.env.example` to `.env` and add your OpenAI API key:
	```sh
	cp .env.example .env
	# Edit .env and set OPENAI_API_KEY=sk-...
	```

## Usage
Start the FastAPI server:
```sh
python -m uvicorn src.main:app --reload
```

Trigger a negotiation (example):
```sh
curl -X POST http://localhost:8000/negotiate \
  -H "Content-Type: application/json" \
  -d '{
    "product": {
      "name": "Laptop",
      "listing_price": 1200
    },
    "seller_min_price": 900,
    "buyer_max_price": 1100
  }' | jq .
```

## Marketplace Listings (SQLite)

This branch adds a simple SQLite-backed listings store to support a dummy marketplace.

### What was added
- SQLite database (`app.db`) created automatically on server startup
- `Listing` table + seed data (10 dummy listings)
- CRUD-style endpoints to fetch/create listings
- Simple keyword search via query param `q`

### How to test
- Open Swagger UI: `http://127.0.0.1:8000/docs`

- List all dummy listings:
  ```sh
  curl http://127.0.0.1:8000/listings
  ```

- Search listings (title/description):
  ```sh
  curl "http://127.0.0.1:8000/listings?q=iphone"
  ```

- Get a listing by id:
  ```sh
  curl http://127.0.0.1:8000/listings/1
  ```

- Create a new listing:
  ```sh
  curl -X POST http://127.0.0.1:8000/listings \
    -H "Content-Type: application/json" \
    -d '{
      "title": "Standing Desk",
      "description": "Electric, works great",
      "price": 180,
      "category": "furniture"
    }'
  ```

### Notes
- Seeding runs only if the `listings` table is empty. To re-seed during development, delete `app.db` and restart the server.
- `app.db` is ignored via `.gitignore`.

### How it Works
1. **Listing**: The negotiation starts with the Seller's `listing_price`.
2. **Haggling**:
   - The **Buyer Agent** (aware of its max budget) makes a counter-offer below the listing price.
   - The **Seller Agent** (aware of its min floor) responds with a new offer.
3. **Consensus**: The negotiation continues until one agent accepts the other's offer by repeating the price (or making an offer within a negligible difference), or until the max rounds are reached.
4. **Result**: The API returns the full transcript, the final price, and the reason for the agreement (or failure).

## Testing
Run all automated tests (uses mocks, no real API calls):
```sh
pytest tests/ -v
```

## Project Structure
- `src/` - main backend code (agents, negotiation logic, FastAPI app)
- `tests/` - automated tests (mocked agents, negotiation, API)

---
This PoC is for research and demonstration purposes only.
