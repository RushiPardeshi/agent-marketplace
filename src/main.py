from fastapi import FastAPI, HTTPException, Depends, Body, Path, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from src.services.negotiation import NegotiationService
from src.services.search import SearchService
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
    SearchRequest,
    SearchResponse,
    ParsedQuery,
    SearchResult,
)
from openai import OpenAI
from src.config import settings
from dotenv import load_dotenv
import json
import uuid
from typing import Dict, Any
from starlette.concurrency import run_in_threadpool
import time
import redis
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
search_service = SearchService()

# Reusable OpenAI client for refinement suggestions
suggestion_client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Redis for chat state persistence
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Helper functions for (de)serializing chat state with Pydantic models
def _state_to_redis_dict(state: Dict[str, Any]) -> Dict[str, Any]:
    """Convert in-memory state (may contain Pydantic models) into JSON-serializable dict."""
    out: Dict[str, Any] = dict(state)

    parsed = out.get("parsed")
    if isinstance(parsed, ParsedQuery):
        out["parsed"] = parsed.model_dump() if hasattr(parsed, "model_dump") else parsed.dict()

    results = out.get("results")
    if isinstance(results, list) and results and isinstance(results[0], SearchResult):
        ser = []
        for r in results:
            ser.append(r.model_dump() if hasattr(r, "model_dump") else r.dict())
        out["results"] = ser

    return out


def _state_from_redis_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Redis-loaded dict into in-memory state with Pydantic models."""
    state: Dict[str, Any] = dict(data)

    parsed = state.get("parsed")
    if isinstance(parsed, dict):
        try:
            state["parsed"] = ParsedQuery(**parsed)
        except Exception:
            state["parsed"] = None

    results = state.get("results")
    if isinstance(results, list) and results and isinstance(results[0], dict):
        rebuilt: list = []
        for r in results:
            try:
                rebuilt.append(SearchResult(**r))
            except Exception:
                # If a single result fails to parse, skip it
                continue
        state["results"] = rebuilt

    return state

def load_chat_state(session_id: str) -> Dict[str, Any]:
    """Load chat state from Redis."""
    data = redis_client.get(f"chat:{session_id}")
    if data:
        return _state_from_redis_dict(json.loads(data))
    return {
        "state": "idle",
        "parsed": None,
        "results": [],
        "history": [],
        "last_query": None,
        "rate_limit": {"searches": 0, "last_reset": time.time()},
    }

def save_chat_state(session_id: str, state: Dict[str, Any]):
    """Save chat state to Redis with 1-hour expiry."""
    payload = _state_to_redis_dict(state)
    redis_client.setex(f"chat:{session_id}", 3600, json.dumps(payload))

def delete_chat_state(session_id: str):
    """Delete chat state from Redis."""
    redis_client.delete(f"chat:{session_id}")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_listings(db)
        # Skip embedding refresh on startup to avoid blocking
        # The index will be built lazily on first search
        # search_service.refresh_index(db)
    finally:
        db.close()

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/negotiate", response_model=NegotiationResult)
def negotiate(
    request: NegotiationRequest = Body(
        ...,
        examples={
            "default": {
                "summary": "Basic negotiation request",
                "value": {
                    "product": {
                        "name": "Laptop",
                        "description": "Lightly used, includes charger",
                        "listing_price": 1200,
                    },
                    "seller_min_price": 900,
                    "buyer_max_price": 1100,
                    "active_competitor_sellers": 1,
                    "active_interested_buyers": 5,
                    "initial_seller_offer": None,
                    "initial_buyer_offer": None,
                    "seller_patience": None,
                    "buyer_patience": None,
                },
            }
        },
    )
):
    try:
        result = negotiation_service.negotiate(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# New endpoint: Negotiate for a specific listing, ensuring product fields match the listing in DB.
@app.post("/listings/{listing_id}/negotiate", response_model=NegotiationResult)
def negotiate_for_listing(
    listing_id: int = Path(..., examples={"default": {"value": 8}}),
    request: ListingNegotiationRequest = Body(
        ...,
        examples={
            "default": {
                "summary": "Negotiation against a listing",
                "value": {
                    "seller_min_price": 700,
                    "buyer_max_price": 900,
                    "active_competitor_sellers": 1,
                    "active_interested_buyers": 2,
                    "initial_seller_offer": None,
                    "initial_buyer_offer": None,
                    "seller_patience": None,
                    "buyer_patience": None,
                },
            }
        },
    ),
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

@app.post("/search", response_model=SearchResponse)
def search_products(
    request: SearchRequest = Body(
        ...,
        examples={
            "default": {
                "summary": "Search query",
                "value": {
                    "query": "I need a gaming laptop with at least 16GB RAM under $1500",
                    "user_budget": 1500.0,
                    "top_k": 5,
                    "use_vector": True
                },
            }
        },
    ),
    db: Session = Depends(get_db),
):
    try:
        result = search_service.perform_search(request, db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/test")
async def test_websocket(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"message": "Connected to test endpoint"})
    await websocket.close()

@app.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Create new session
    session_id = str(uuid.uuid4())
    state = await run_in_threadpool(load_chat_state, session_id)

    # Let the client know the session id (useful for debugging/UI)
    await websocket.send_json({"type": "session", "session_id": session_id})

    try:
        while True:
            # -------------
            # Receive + validate JSON
            # -------------
            try:
                raw = await websocket.receive_text()
            except Exception:
                await websocket.send_json({"type": "error", "message": "Failed to receive message"})
                continue

            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            if not isinstance(message, dict) or "type" not in message:
                await websocket.send_json({"type": "error", "message": "Message must be a JSON object with a 'type' field"})
                continue

            msg_type = message.get("type")

            # Handle resume session
            if msg_type == "resume" and state.get("state") == "idle":
                old_session_id = message.get("session_id")
                if old_session_id:
                    old_state = await run_in_threadpool(load_chat_state, old_session_id)
                    if old_state:
                        state = old_state
                        session_id = old_session_id
                        await websocket.send_json({"type": "resumed", "session_id": session_id})
                        continue
                await websocket.send_json({"type": "error", "message": "Session not found or invalid"})
                continue

            if state is None:
                await websocket.send_json({"type": "error", "message": "Session not found"})
                continue

            # Rate limiting: max 10 searches per minute per session
            now = time.time()
            rl = state["rate_limit"]
            if now - rl["last_reset"] > 60:
                rl["searches"] = 0
                rl["last_reset"] = now
            if msg_type == "user_query" and rl["searches"] >= 10:
                await websocket.send_json({"type": "error", "message": "Rate limit exceeded. Try again later."})
                continue

            # Logging
            print(f"Session {session_id}: {msg_type}")

            # Save history
            state["history"].append({"role": "user", "content": message})

            # -------------
            # Handle message types
            # -------------
            if msg_type == "user_query":
                query = message.get("content")
                if not isinstance(query, str) or not query.strip():
                    await websocket.send_json({"type": "error", "message": "user_query requires non-empty 'content' string"})
                    continue

                state["last_query"] = query

                # Run sync OpenAI parsing off the event loop
                parsed = await run_in_threadpool(search_service.parse_query, query, None)

                if getattr(parsed, "parse_confidence", 0.0) < 0.7:
                    await websocket.send_json({
                        "type": "clarify",
                        "message": (
                            "I'm not fully sure what you want yet. "
                            "Can you clarify budget/specs/category? "
                            f"(confidence: {getattr(parsed, 'parse_confidence', 0.0):.2f})"
                        ),
                        "parsed_query": parsed.model_dump() if hasattr(parsed, "model_dump") else None,
                    })
                    state["state"] = "clarifying"
                    state["parsed"] = parsed

                    # Save state
                    await run_in_threadpool(save_chat_state, session_id, state)
                    continue

                # Perform full search in a threadpool with safe DB session
                def _do_search(q: str):
                    db = SessionLocal()
                    try:
                        return search_service.perform_search(SearchRequest(query=q), db)
                    finally:
                        db.close()

                response = await run_in_threadpool(_do_search, query)

                state["parsed"] = parsed
                state["results"] = response.results
                state["state"] = "searched"

                # Increment rate limit
                state["rate_limit"]["searches"] += 1

                # Save state
                await run_in_threadpool(save_chat_state, session_id, state)

                # If poor results, generate suggestion
                if len(response.results) == 0:
                    suggestion = await run_in_threadpool(generate_refinement_suggestion, parsed, "no_results")
                    await websocket.send_json({
                        "type": "search_results",
                        "data": response.model_dump() if hasattr(response, "model_dump") else response.dict(),
                        "suggestion": suggestion,
                    })
                elif len(response.results) < 3:
                    suggestion = await run_in_threadpool(generate_refinement_suggestion, parsed, "few_results")
                    await websocket.send_json({
                        "type": "search_results",
                        "data": response.model_dump() if hasattr(response, "model_dump") else response.dict(),
                        "suggestion": suggestion,
                    })
                else:
                    await websocket.send_json({
                        "type": "search_results",
                        "data": response.model_dump() if hasattr(response, "model_dump") else response.dict(),
                    })

            elif msg_type == "apply_refinement":
                # Example: {"type": "apply_refinement", "new_budget": 1200}
                parsed = state.get("parsed")
                last_query = state.get("last_query")

                if parsed is None or not isinstance(last_query, str) or not last_query.strip():
                    await websocket.send_json({"type": "error", "message": "No active search to refine"})
                    continue

                new_budget = message.get("new_budget")
                if new_budget is None:
                    await websocket.send_json({"type": "error", "message": "apply_refinement currently requires 'new_budget'"})
                    continue
                try:
                    new_budget_f = float(new_budget)
                    if new_budget_f <= 0:
                        raise ValueError
                except Exception:
                    await websocket.send_json({"type": "error", "message": "new_budget must be a positive number"})
                    continue

                # Update parsed query in state
                try:
                    parsed.max_budget = new_budget_f
                    state["parsed"] = parsed
                except Exception:
                    pass

                # Re-run search using the original query + explicit budget override
                def _do_search_refined(q: str, budget: float):
                    db = SessionLocal()
                    try:
                        return search_service.perform_search(SearchRequest(query=q, user_budget=budget), db)
                    finally:
                        db.close()

                response = await run_in_threadpool(_do_search_refined, last_query, new_budget_f)
                state["results"] = response.results
                state["state"] = "searched"

                await websocket.send_json({
                    "type": "updated_results",
                    "data": response.model_dump() if hasattr(response, "model_dump") else response.dict(),
                })

                # Save state
                await run_in_threadpool(save_chat_state, session_id, state)

            elif msg_type == "negotiate":
                if state.get("state") != "searched":
                    await websocket.send_json({"type": "error", "message": "Run a search before negotiating"})
                    continue

                listing_id = message.get("listing_id")
                try:
                    listing_id_int = int(listing_id)
                except Exception:
                    await websocket.send_json({"type": "error", "message": "negotiate requires integer 'listing_id'"})
                    continue

                # Re-fetch listing from DB (source of truth)
                def _load_listing(lid: int):
                    db = SessionLocal()
                    try:
                        return db.query(Listing).filter(Listing.id == lid).first()
                    finally:
                        db.close()

                listing = await run_in_threadpool(_load_listing, listing_id_int)
                if not listing:
                    await websocket.send_json({"type": "error", "message": "Listing not found"})
                    continue

                # Determine budget from parsed state
                parsed = state.get("parsed")
                max_budget = getattr(parsed, "max_budget", None)

                # If budget is unknown, allow negotiation up to listing price (safe default)
                buyer_max = float(max_budget) if max_budget is not None else float(listing.price)

                # Build negotiation request (sync) and run in threadpool
                def _do_negotiate():
                    req = NegotiationRequest(
                        product=Product(
                            name=listing.title,
                            description=listing.description,
                            listing_price=float(listing.price),
                        ),
                        seller_min_price=float(listing.price) * 0.8,
                        buyer_max_price=buyer_max,
                        active_competitor_sellers=1,
                        active_interested_buyers=1,
                    )
                    return negotiation_service.negotiate(req)

                neg_result = await run_in_threadpool(_do_negotiate)

                await websocket.send_json({
                    "type": "negotiation_result",
                    "data": neg_result.model_dump() if hasattr(neg_result, "model_dump") else neg_result.dict(),
                })

            elif msg_type == "reset":
                # Reset session state
                state = {
                    "state": "idle",
                    "parsed": None,
                    "results": [],
                    "history": [],
                    "last_query": None,
                    "rate_limit": {"searches": 0, "last_reset": time.time()},
                }
                await websocket.send_json({"type": "reset_ack", "message": "Session reset."})

                # Save reset state
                await run_in_threadpool(save_chat_state, session_id, state)

            else:
                await websocket.send_json({"type": "error", "message": f"Unknown message type: {msg_type}"})

    except WebSocketDisconnect:
        pass
    finally:
        # Do not delete chat state on disconnect; Redis TTL (1 hour) will expire it.
        # This enables persistence across reconnects/restarts when the client reuses session_id.
        await run_in_threadpool(save_chat_state, session_id, state)

def generate_refinement_suggestion(parsed: Any, reason: str) -> str:
    """Use LLM to suggest refinements based on poor results."""
    max_budget = getattr(parsed, "max_budget", None)
    product_type = getattr(parsed, "product_type", None)
    description = getattr(parsed, "description", None)

    prompt = (
        f"User searched for: {(product_type or 'product')} {(description or '')} "
        f"under ${max_budget if max_budget is not None else 'any'}.\n"
        f"Reason: {reason} (no_results or few_results).\n"
        "Suggest 1-2 specific refinements (e.g., increase budget to $X, add/remove a spec, change category). "
        "Keep it short, helpful, and actionable."
    )

    resp = suggestion_client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=80,
        temperature=0.2,
    )
    return (resp.choices[0].message.content or "").strip()