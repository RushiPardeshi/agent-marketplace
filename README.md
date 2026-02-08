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
- **Search Copilot**: AI-powered natural language search with semantic matching using OpenAI embeddings
- **WebSocket Chat**: Real-time conversational interface for search, refinement suggestions, and negotiation
- **Redis State Persistence**: Session state persists across reconnections (1-hour TTL)

## Setup
1. Clone the repo and install dependencies:
	```sh
	pip install -r requirements.txt
	```
2. Install WebSocket support (required for chat interface):
	```sh
	pip install 'uvicorn[standard]'
	```
3. Install and start Redis (required for WebSocket state persistence):
	```sh
	# macOS
	brew install redis
	redis-server
	
	# Verify Redis is running
	redis-cli ping  # Should return: PONG
	```
4. Copy `.env.example` to `.env` and add your OpenAI API key:
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

## Search Copilot (AI-Powered Semantic Search)

The search copilot uses OpenAI embeddings for intelligent product matching and natural language query parsing.

### REST API Search
```sh
curl -X POST http://127.0.0.1:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "gaming laptop under $1500 with 16GB RAM",
    "top_k": 5,
    "use_vector": true
  }'
```

**Expected Response:**
```json
{
  "parsed_query": {
    "product_type": "laptop",
    "description": "gaming, 16GB RAM",
    "max_budget": 1500.0,
    "parse_confidence": 0.9
  },
  "results": [
    {
      "listing": {"id": 1, "title": "Gaming Laptop", "price": 1200.0, ...},
      "relevance_score": 0.95,
      "reasons": ["Semantic match", "Within budget"],
      "negotiation_ready": true
    }
  ],
  "message": "Found 3 matches for 'laptop' under $1500.0."
}
```

### WebSocket Chat Interface

The chat provides a conversational experience combining search, refinements, and negotiation.

#### Connect to Chat
```sh
# Using websocat (install: brew install websocat)
websocat ws://127.0.0.1:8000/ws/chat
```

**Initial Response:**
```json
{"type":"session","session_id":"uuid-here"}
```

#### Step 1: Search for Products
Send (type JSON on one line):
```json
{"type":"user_query","content":"I want a gaming laptop under $1500"}
```

**Expected:**
```json
{
  "type":"search_results",
  "data": {
    "parsed_query": {...},
    "results": [...],
    "message": "Found 3 matches..."
  }
}
```

#### Step 2: Apply Refinement
If you receive a `suggestion` field (when <3 results found):
```json
{"type":"apply_refinement","new_budget":1200}
```

**Expected:**
```json
{"type":"updated_results","data":{...}}
```

#### Step 3: Negotiate on a Listing
Pick a `listing_id` from search results:
```json
{"type":"negotiate","listing_id":5}
```

**Expected:**
```json
{
  "type":"negotiation_result",
  "data":{
    "agreed": true,
    "final_price": 1150,
    "turns": [
      {"round":1,"agent":"buyer","offer":950,"message":"..."},
      {"round":2,"agent":"seller","offer":1200,"message":"..."}
    ]
  }
}
```

#### Step 4: Reset Session
```json
{"type":"reset"}
```

**Expected:**
```json
{"type":"reset_ack","message":"Session reset."}
```

### Special Chat Features

#### Clarification for Vague Queries
When query confidence < 0.7:
```json
{"type":"user_query","content":"I want something"}
```

**Expected:**
```json
{
  "type":"clarify",
  "message":"I'm not fully sure what you want yet. Can you clarify budget/specs/category? (confidence: 0.30)"
}
```

#### Proactive Suggestions for Poor Results
When 0-2 results are found:
```json
{"type":"user_query","content":"I want a MacBook Pro under $200"}
```

**Expected:**
```json
{
  "type":"search_results",
  "data":{...},
  "suggestion":"No MacBook Pros under $200. Typical prices are $1200-$2000. Try increasing budget to $1500?"
}
```

#### Session Persistence (Redis)
Sessions persist for 1 hour and survive server restarts:
1. Search for something, note the `session_id`
2. Disconnect (Ctrl+C)
3. Reconnect: `websocat ws://127.0.0.1:8000/ws/chat`
4. Send: `{"type":"resume","session_id":"your-uuid"}`

**Expected:**
```json
{"type":"resumed","session_id":"your-uuid"}
```

#### Rate Limiting
Maximum 10 searches per minute per session. Exceeding this returns:
```json
{"type":"error","message":"Rate limit exceeded. Try again later."}
```

## Troubleshooting

### WebSocket 404 Error
If you get `Received unexpected status code (404 Not Found)`:
```sh
pip install 'uvicorn[standard]'
# or
pip install websockets
```
Then restart the server.

### Redis Connection Error
If you see `redis.exceptions.ConnectionError`:
```sh
redis-server  # Start Redis
redis-cli ping  # Verify (should return PONG)
```

### Empty Search Results
Delete `app.db` and restart server to re-seed listings.

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
