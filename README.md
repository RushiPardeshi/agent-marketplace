# agent-marketplace

## Overview
Proof of Concept: Can a seller AI agent and a buyer AI agent reach an agreement through negotiation? This FastAPI backend simulates automated price negotiation using OpenAI's GPT models.

## Features
- **Smart Agents**: Seller and buyer agents negotiate price for a product, acting as advocates for their respective users.
- **Listing Price**: Negotiations start from a public listing price set by the seller.
- **Realistic Haggling**: Agents negotiate like humans, using strategic lowball/highball anchors and making incremental concessions.
- **Dynamic Patience**: The number of negotiation rounds is dynamically calculated based on market conditions (supply/demand).
- **Market Leverage**: Agents adjust their strategy (aggressive vs. stubborn) based on the number of active competitors and interested buyers.
- **Turn-based**: Fully automated negotiation loop that ends when a deal is struck or patience runs out.
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
    "buyer_max_price": 1100,
    "active_competitor_sellers": 1,
    "active_interested_buyers": 5
  }' | jq .
```

Trigger a negotiation for a listing in the SQLite DB (by listing id):
```sh
curl -X POST http://localhost:8000/listings/8/negotiate \
  -H "Content-Type: application/json" \
  -d '{
    "seller_min_price": 250,
    "buyer_max_price": 320,
    "active_competitor_sellers": 1,
    "active_interested_buyers": 2
  }' | jq .
```

Human-Agent negotiation (CLI conversational flow):
```sh
python -m src.cli.negotiate \
  --role buyer \
  --product-name "Laptop" \
  --product-description "Lightly used, includes charger" \
  --listing-price 1200 \
  --seller-min-price 900 \
  --active-competitor-sellers 1 \
  --active-interested-buyers 5
```

Notes:
- The CLI prompts you for offers and short messages each turn.
- Use `accept` to accept the last offer.
- If the human is the buyer, you only need to provide `seller_min_price` (buyer max is not required).
- If the human is the seller, you only need to provide `buyer_max_price` (seller min is not required).
- The transcript is printed and saved to `./negotiation_outputs/` by default (or pass `--output-path`).

## Marketplace Listings (SQLite)

This repo includes a simple SQLite-backed listings store to support a dummy marketplace.

### What this means
- **SQLite is file-based**: there is **no separate SQLite server** to run.
- When you start the FastAPI app, it opens/creates a local database file named **`app.db`** in the project root.

### What was added
- SQLite database file: `app.db` (auto-created on startup)
- `Listing` table + **10 seeded dummy listings** (seed runs only when the table is empty)
- REST endpoints to list/search/fetch/create listings

### How to access listings (API)
- **List all listings**
  ```sh
  curl http://127.0.0.1:8000/listings
  ```

- **Search listings** (matches `title` and `description`)
  ```sh
  curl "http://127.0.0.1:8000/listings?q=iphone"
  ```

- **Get listing by id**
  ```sh
  curl http://127.0.0.1:8000/listings/1
  ```

- **Create a new listing**
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

### Expected output
- `GET /listings` returns a JSON array of listings (typically **10 items** right after a fresh seed). Example:
  ```json
  [
    {
      "id": 10,
      "title": "Textbook Bundle (CS)",
      "description": "Algorithms + ML intro books. Great condition.",
      "price": 40.0,
      "category": "books"
    }
  ]
  ```

- `GET /listings?q=iphone` returns a filtered JSON array (0+ results).

- `GET /listings/{id}` returns a single listing object. If the id does not exist, you get a **404**:
  ```json
  {"detail": "Listing not found"}
  ```

- `POST /listings` returns the created listing including its new `id`.

### How to test
- Swagger UI: `http://127.0.0.1:8000/docs`
  - Try `GET /listings` and confirm you see the seeded listings.

### Notes / common gotchas
- **Seed behavior**: seeding runs only if the `listings` table is empty.
  - To reset during development: stop the server, delete `app.db`, then restart.
- `app.db` is ignored via `.gitignore` (it should not be committed).

### How it Works
1. **Listing**: The negotiation starts with the Seller's `listing_price`.
2. **Market Context**: The system calculates "leverage" for each agent based on `active_competitor_sellers` vs. `active_interested_buyers`. This determines how "patient" (how many rounds) each agent is willing to wait.
3. **Haggling**:
   - The **Buyer Agent** (aware of its max budget) makes a counter-offer below the listing price.
   - The **Seller Agent** (aware of its min floor) responds with a new offer.
   - Agents use strategies like "lowballing" or "holding firm" depending on their calculated leverage.
4. **Consensus**: The negotiation continues until one agent accepts the other's offer, or until an agent's patience runs out (deadlock).
5. **Result**: The API returns the full transcript, the final price, and the reason for the agreement (or failure).

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
