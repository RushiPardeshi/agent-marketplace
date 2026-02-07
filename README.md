# agent-marketplace

## Overview
Proof of Concept: Can a seller AI agent and a buyer AI agent reach an agreement through negotiation? This FastAPI backend simulates automated price negotiation using OpenAI's GPT models.

## Features
- Seller and buyer agents negotiate price for a product
- Negotiation is turn-based, in-memory, and limited to a max number of rounds
- API endpoint to trigger negotiation and get full negotiation history
- Automated tests with mocked LLM calls for fast, free, deterministic testing

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
  -d '{"product": {"name": "Laptop"}, "seller_min_price": 900, "buyer_max_price": 1200}'
```

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