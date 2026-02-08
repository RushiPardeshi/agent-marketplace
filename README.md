# agent-marketplace

## Overview
Proof of Concept: Can AI agents (sellers and buyers) reach agreements through negotiation in a marketplace? This FastAPI backend simulates automated price negotiation using OpenAI's GPT models.

**Now supports multi-agent marketplace scenarios** with multiple buyers and sellers negotiating simultaneously, with the ability to switch between sellers and track competitive dynamics.

## Features
- **Smart Agents**: Seller and buyer agents negotiate price for a product, acting as advocates for their respective users.
- **Multi-Agent Marketplace**: Support for multiple buyers and sellers negotiating simultaneously in a free market
- **Automated Sessions**: Run entire negotiation sessions automatically with agent autonomy
- **Agent Autonomy**: Buyer agents can autonomously decide when to switch sellers based on negotiation progress
- **Buyer Preferences**: Buyers specify which sellers they're interested in; can add more sellers later
- **Deal Finality**: Once a deal is made, both buyer and seller become inactive (product is sold)
- **Seller Switching**: Buyers can end negotiations and switch between sellers without lock-in
- **Marketplace Visibility**: Agents are aware of competitive dynamics (number of buyers/sellers) to inform strategy
- **Listing Price**: Negotiations start from a public listing price set by the seller.
- **Realistic Haggling**: Agents negotiate like humans, using strategic lowball/highball anchors and making incremental concessions.
- **Dynamic Patience**: The number of negotiation rounds is dynamically calculated based on market conditions (supply/demand).
- **Market Leverage**: Agents adjust their strategy (aggressive vs. stubborn) based on the number of active competitors and interested buyers.
- **Turn-based**: Fully automated negotiation loop that ends when a deal is struck or patience runs out.
- **In-Memory Sessions**: Repository pattern for easy migration to Postgres/Supabase in the future
- **Testing**: Automated tests with mocked LLM calls for fast, free, deterministic testing.
- **Search Copilot**: AI-powered natural language search with semantic matching using OpenAI embeddings
- **WebSocket Chat**: Real-time conversational interface for search, refinement suggestions, and negotiation
- **Redis State Persistence**: Session state persists across reconnections (1-hour TTL)
- **Realtime Listing Negotiations**: Buyer and seller chat in the same listing thread via WebSocket

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

### Frontend (React + Vite)
```sh
cd frontend
npm install
npm run dev
```

By default, the frontend calls `http://localhost:8000`. You can override this with:
```sh
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

Notes:
- The UI derives market context from the current session (e.g., number of search results) rather than manual inputs.
- If a search query does not include a budget, the UI prompts for a maximum budget before negotiating.
- Listing chats are real-time and shared between buyer and seller tabs.

### Single Agent Negotiation
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

### Multi-Agent Marketplace

The multi-agent API enables scenarios with multiple buyers and sellers negotiating in parallel.

#### Create a Session

**Note:** Buyers must specify which sellers they're interested in via `interested_seller_ids`. They can only negotiate with sellers in this list (but can add more later).

```sh
curl -X POST http://localhost:8000/multi-agent/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "buyers": [
      {"agent_id": "buyer_1", "max_price": 900, "interested_seller_ids": ["seller_1", "seller_2"]},
      {"agent_id": "buyer_2", "max_price": 70, "interested_seller_ids": ["seller_2"]}
    ],
    "sellers": [
      {"agent_id": "seller_1", "listing_id": 1, "min_price": 700},
      {"agent_id": "seller_2", "listing_id": 2, "min_price": 40}
    ]
  }' | jq .
```

**Note:** The `listing_price` is automatically fetched from the database using `listing_id`. You can optionally override it by specifying `listing_price` in the seller config.

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "buyers": {"buyer_1": {...}, "buyer_2": {...}},
  "sellers": {"seller_1": {...}, "seller_2": {...}},
  "marketplace_context": {
    "total_active_buyers": 2,
    "total_active_sellers": 2,
    "active_negotiations_count": 0
  }
}
```

#### Start Buyer-Seller Negotiation
```sh
curl -X POST http://localhost:8000/multi-agent/sessions/{session_id}/negotiations \
  -H "Content-Type: application/json" \
  -d '{
    "buyer_id": "buyer_1",
    "seller_id": "seller_1"
  }' | jq .
```

#### Execute Negotiation Turn
```sh
curl -X POST http://localhost:8000/multi-agent/sessions/{session_id}/negotiations/{negotiation_id}/turn \
  -H "Content-Type: application/json" | jq .
```

**Response:**
```json
{
  "turn": {
    "round": 1,
    "agent_id": "buyer_1",
    "agent_role": "buyer",
    "offer": 900,
    "message": "I'd like to offer $900 for this laptop..."
  },
  "negotiation_status": {
    "negotiation_id": "...",
    "status": "active",
    "buyer_leverage": "medium",
    "seller_leverage": "medium"
  }
}
```

#### Switch Seller
Buyers can end current negotiation and switch to another seller:
```sh
curl -X POST http://localhost:8000/multi-agent/sessions/{session_id}/switch \
  -H "Content-Type: application/json" \
  -d '{
    "buyer_id": "buyer_1",
    "current_seller_id": "seller_1",
    "new_seller_id": "seller_2" 
  }' | jq .
```

#### View Session Status
```sh
curl http://localhost:8000/multi-agent/sessions/{session_id} | jq .
```

**Response includes:**
- All active negotiations
- All completed negotiations (agreed, deadlock, switched)
- Marketplace context with supply/demand metrics

#### Get Negotiation Transcript
```sh
curl http://localhost:8000/multi-agent/sessions/{session_id}/negotiations/{negotiation_id}/transcript | jq .
```

**Returns full turn-by-turn history with:**
- Agent IDs and roles
- Offers and messages
- Negotiation outcome

#### Add Seller to Buyer Interests
Allow a buyer to add more sellers to their interest list after session creation:
```sh
curl -X POST http://localhost:8000/multi-agent/sessions/{session_id}/add-seller-interest \
  -H "Content-Type: application/json" \
  -d '{
    "buyer_id": "buyer_1",
    "seller_id": "seller_3"
  }' | jq .
```

#### Automate Entire Session
Run the entire session automatically with agent autonomy. Buyer agents will negotiate with their interested sellers and can autonomously decide to switch sellers. Once a deal is made, both buyer and seller become inactive.

```sh
curl -X POST http://localhost:8000/multi-agent/sessions/{session_id}/automate \
  -H "Content-Type: application/json" \
  -d '{
    "max_rounds_per_negotiation": 20,
    "allow_agent_switching": true
  }' | jq .
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "summary": {
    "total_deals": 2,
    "total_deadlocks": 0,
    "total_switches": 1,
    "total_rounds": 15
  },
  "deals": [
    {
      "buyer_id": "buyer_1",
      "seller_id": "seller_2",
      "final_price": 825,
      "rounds": 8
    }
  ],
  "deadlocks": [],
  "switches": [
    {
      "buyer_id": "buyer_1",
      "from_seller": "seller_1",
      "to_seller": "seller_2",
      "rounds_before_switch": 5
    }
  ]
}
```

**How Agent Autonomy Works:**

1. **Buyer Decides to Switch**: Buyer agents autonomously decide to switch sellers based on:
   - Stuck for 3+ rounds with no progress
   - Seller asking 15%+ above buyer's budget with few rounds left
   - Buyer made many concessions but seller barely budged
   - Must have alternative sellers available in their interest list

2. **Deal Finality**: Once a buyer-seller pair agrees on a price:
   - Both agents are marked as inactive
   - They stop participating in all negotiations
   - Product is considered sold
   - Active buyer/seller counts are updated

3. **Session Completion**: The automated session runs until:
   - All buyers have made deals (or exhausted options)
   - All sellers have sold their products
   - All active negotiations reach deadlock or max rounds

## Marketplace Listings (SQLite)

This repo includes a simple SQLite-backed listings store to support a dummy marketplace.

### What this means
- **SQLite is file-based**: there is **no separate SQLite server** to run.
- When you start the FastAPI app, it opens/creates a local database file named **`app.db`** in the project root.

### What was added
- SQLite database file: `app.db` (auto-created on startup)
- `Listing` table + **10 seeded dummy listings** (seed runs only when the table is empty)
- REST endpoints to list/search/fetch/create listings
- Seller min price is stored on listings (kept private; not returned in listing responses)

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
      "category": "furniture",
      "seller_min_price": 140
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

### Realtime Listing Negotiation (WebSocket)

Each listing has a shared negotiation room. Buyer and seller can both join and see the same chat.

#### Connect
```sh
websocat ws://127.0.0.1:8000/ws/negotiations/{listing_id}
```

#### Join (send once after connect)
```json
{"role":"buyer","name":"Alice","counterparty":"human","buyer_max_price":900}
```

```json
{"role":"seller","name":"Bob","counterparty":"human","seller_min_price":700}
```

To negotiate with an agent instead of a human, set `counterparty` to `"agent"`.

#### Send an offer
```json
{"type":"offer","offer":850,"message":"Can you do $850?"}
```

#### Receive updates
```json
{"type":"turn","turn":{"round":1,"agent":"buyer","offer":850,"message":"Can you do $850?","name":"Alice"}}
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

### Multi-Agent Architecture

The multi-agent marketplace extends the single buyer-seller negotiation to support:

#### Free Market Design
- **Buyer Preferences**: Buyers specify interested sellers upfront; can only negotiate with sellers in their list
- **Add More Sellers**: Buyers can expand their interest list anytime via API
- **Manual Pairing**: Buyers explicitly choose which seller to negotiate with (no automatic matching)
- **Agent Autonomy**: Buyer agents can autonomously decide to switch sellers based on negotiation progress
- **No Lock-In**: Buyers can end negotiations and switch sellers at any time
- **Deal Finality**: Once a deal is made, both buyer and seller become inactive (product sold)
- **Full Visibility**: All agents see marketplace context (total buyers/sellers, active negotiations)

#### Session Management
- **In-Memory Storage**: Uses repository pattern for flexible storage (easy migration to Postgres/Supabase)
- **Session State**: Tracks all buyers, sellers, active/completed negotiations in one session
- **Active Status**: Buyers and sellers marked inactive after making deals
- **Marketplace Context**: Real-time supply/demand metrics inform agent leverage calculations

#### Negotiation Flow
1. **Session Creation**: Define multiple buyers (with max prices, interested sellers) and sellers (with min prices, listings)
2. **Start Negotiation**: Pair one buyer with one seller for 1-1 negotiation (validates buyer interest)
3. **Execute Turns**: Each turn alternates between buyer and seller with marketplace awareness
4. **Autonomous Switching**: Buyer agent can decide to switch sellers based on progress criteria
5. **Manual Switching**: Buyer can also explicitly switch from one seller to another
6. **Deal Completion**: When agreed, both agents marked inactive and removed from market
7. **Track Outcomes**: Negotiations end with status: `agreed`, `deadlock`, `switched`

#### Automated Sessions
The `POST /automate` endpoint runs entire sessions automatically:
- Each buyer negotiates with their first interested seller
- Buyer agents autonomously switch if:
  - Stuck for 3+ rounds without progress
  - Seller asking 15%+ above budget with few rounds left
  - Buyer made many concessions but seller barely budged
- Once a deal is made, both agents become inactive
- Session completes when all possible deals are made or deadlocked

#### Dynamic Leverage
- **High Buyer Leverage**: Many sellers (3+) → buyers more aggressive
- **High Seller Leverage**: Many buyers (3+) → sellers more aggressive  
- **Medium/Low**: Balanced or single-party markets → more cautious strategies

#### Safeguards
- **Monotonic Prices**: Sellers never increase offers, buyers never decrease offers
- **Stall Detection**: If both parties hold firm for 2+ rounds, trigger final offer mechanism
- **Structured State**: Agents receive offer history directly (no brittle string parsing)

## Testing
Run all automated tests (uses mocks, no real API calls):
```sh
pytest tests/ -v
```

Run specific test suites:
```sh
# Single-agent negotiation tests
pytest tests/test_negotiation.py -v

# Multi-agent marketplace tests
pytest tests/test_multi_agent.py -v

# Agent behavior tests (including monotonic price safeguards)
pytest tests/test_agents.py -v
```

## Project Structure
- `src/` - main backend code
  - `agents/` - Base, Buyer, Seller agent implementations
  - `models/` - Database models and Pydantic schemas
  - `services/` - Negotiation orchestration (single & multi-agent)
  - `repositories/` - Session storage abstraction (in-memory with DB migration path)
  - `main.py` - FastAPI application with REST endpoints
- `tests/` - automated tests
  - `test_negotiation.py` - Single-agent negotiation tests
  - `test_multi_agent.py` - Multi-agent marketplace tests
  - `test_agents.py` - Agent behavior and safeguards
  - `test_api.py` - API endpoint tests

## Future Enhancements

The multi-agent marketplace provides a foundation for:
- **Database Persistence**: Migrate from in-memory to Postgres/Supabase using existing repository interface
- **Advanced Matching**: Automatic buyer-seller pairing based on preferences and history
- **Reputation System**: Track agent success rates and negotiation styles
- **Concurrent Negotiations**: Buyers negotiating with multiple sellers simultaneously
- **Multi-Round Auctions**: Support for sealed bids, Dutch auctions, etc.
- **CLI for Multi-Agent**: Extend `src/cli/negotiate.py` to support multi-agent sessions

---
This PoC is for research and demonstration purposes only.
