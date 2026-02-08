from fastapi import FastAPI, HTTPException, Depends, Body, Path, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from src.services.negotiation import NegotiationService
from src.services.multi_agent_negotiation import MultiAgentNegotiationService
from src.agents.seller import SellerAgent
from src.agents.buyer import BuyerAgent
from src.services.search import SearchService
from src.repositories import InMemorySessionRepository
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
    CreateSessionRequest,
    StartNegotiationRequest,
    AutomateSessionRequest,
    SessionResponse,
    BuyerConfig,
    SellerConfig,
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

# Multi-agent negotiation service with in-memory repository
session_repository = InMemorySessionRepository()
multi_agent_service = None  # Will be initialized with DB dependency

def get_multi_agent_service(db: Session = Depends(get_db)) -> MultiAgentNegotiationService:
    """Dependency to get multi-agent service with DB connection"""
    return MultiAgentNegotiationService(repository=session_repository, db=db)

# Reusable OpenAI client for refinement suggestions
suggestion_client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Redis for chat state persistence
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# In-memory negotiation rooms for realtime chat
negotiation_rooms: Dict[int, Dict[str, Any]] = {}

def _room_for_listing(listing_id: int) -> Dict[str, Any]:
    if listing_id not in negotiation_rooms:
        negotiation_rooms[listing_id] = {
            "turns": [],
            "buyers": set(),
            "sellers": set(),
            "buyer_max_price": None,
            "seller_min_price": None,
            "buyer_patience": None,
            "seller_patience": None,
            "buyer_delegate": False,
            "seller_delegate": False,
        }
    return negotiation_rooms[listing_id]

def _build_context(turns: list[Dict[str, Any]]) -> str:
    lines = []
    for turn in turns:
        agent = turn.get("agent")
        offer = turn.get("offer")
        message = turn.get("message", "")
        if agent == "buyer":
            lines.append(f"Buyer offers ${offer}: {message}")
        elif agent == "seller":
            lines.append(f"Seller offers ${offer}: {message}")
    return "\n".join(lines)

# Helper functions for (de)serializing chat state with Pydantic models
def _state_to_redis_dict(state: Dict[str, Any]) -> Dict[str, Any]:
    """Convert in-memory state (may contain Pydantic models) into JSON-serializable dict."""
    out: Dict[str, Any] = dict(state)

    parsed = out.get("parsed")
    if isinstance(parsed, ParsedQuery):
        # Pydantic v1: dict(); v2: model_dump()
        out["parsed"] = parsed.dict() if hasattr(parsed, "dict") else parsed.model_dump()

    results = out.get("results")
    if isinstance(results, list) and results and isinstance(results[0], SearchResult):
        ser = []
        for r in results:
            ser.append(r.dict() if hasattr(r, "dict") else r.model_dump())
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
        example={
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
    listing_id: int = Path(..., example=8),
    request: ListingNegotiationRequest = Body(
        ...,
        example={
            "seller_min_price": 700,
            "buyer_max_price": 900,
            "active_competitor_sellers": 1,
            "active_interested_buyers": 2,
            "initial_seller_offer": None,
            "initial_buyer_offer": None,
            "seller_patience": None,
            "buyer_patience": None,
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
    seller_min = request.seller_min_price
    if seller_min is None:
        seller_min = float(listing.seller_min_price) if listing.seller_min_price is not None else float(listing.price) * 0.8

    full_req = NegotiationRequest(
        product=product,
        seller_min_price=seller_min,
        buyer_max_price=request.buyer_max_price,
        active_competitor_sellers=request.active_competitor_sellers,
        active_interested_buyers=request.active_interested_buyers,
        initial_seller_offer=request.initial_seller_offer,
        initial_buyer_offer=request.initial_buyer_offer,
            initial_seller_message=request.initial_seller_message,
            initial_buyer_message=request.initial_buyer_message,
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
    data = payload.model_dump()
    if data.get("seller_min_price") is None:
        data["seller_min_price"] = float(data["price"]) * 0.8
    listing = Listing(**data)
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return ListingOut(
        id=listing.id,
        title=listing.title,
        description=listing.description,
        price=listing.price,
        category=listing.category,
    )

# Multi-Agent Negotiation Endpoints

@app.post("/multi-agent/sessions")
def create_multi_agent_session(
    request: CreateSessionRequest,
    service: MultiAgentNegotiationService = Depends(get_multi_agent_service)
):
    """Create a new multi-agent negotiation session with multiple buyers and sellers"""
    try:
        session = service.create_session(request)
        return {
            "session_id": session.session_id,
            "marketplace_context": session.marketplace_context,
            "buyers": list(session.buyers.keys()),
            "sellers": list(session.sellers.keys()),
            "message": f"Session created with {len(session.buyers)} buyers and {len(session.sellers)} sellers"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/multi-agent/sessions/{session_id}/negotiations")
def start_negotiation_in_session(
    session_id: str,
    request: StartNegotiationRequest,
    service: MultiAgentNegotiationService = Depends(get_multi_agent_service)
):
    """Start a 1-1 negotiation between a buyer and seller"""
    try:
        negotiation = service.start_negotiation(
            session_id=session_id,
            buyer_id=request.buyer_id,
            seller_id=request.seller_id
        )
        return {
            "negotiation_id": negotiation.negotiation_id,
            "buyer_id": negotiation.buyer_id,
            "seller_id": negotiation.seller_id,
            "buyer_leverage": negotiation.buyer_leverage,
            "seller_leverage": negotiation.seller_leverage,
            "status": negotiation.status,
            "message": f"Negotiation started between {request.buyer_id} and {request.seller_id}"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/multi-agent/sessions/{session_id}/negotiations/{negotiation_id}/turn")
def execute_negotiation_turn(
    session_id: str,
    negotiation_id: str,
    service: MultiAgentNegotiationService = Depends(get_multi_agent_service)
):
    """Execute one turn in a specific negotiation"""
    try:
        turn = service.execute_turn(session_id, negotiation_id)
        
        # Get updated negotiation state
        session = service.get_session_status(session_id)
        negotiation = session.active_negotiations.get(negotiation_id)
        if not negotiation:
            # Check completed
            for completed in session.completed_negotiations:
                if completed.negotiation_id == negotiation_id:
                    negotiation = completed
                    break
        
        return {
            "turn": turn,
            "negotiation_status": negotiation.status if negotiation else "unknown",
            "agreed": negotiation.agreed if negotiation else False,
            "final_price": negotiation.final_price if negotiation else None,
            "reason": negotiation.reason if negotiation else None
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/multi-agent/sessions/{session_id}/switch")
def switch_seller_in_session(
    session_id: str,
    buyer_id: str = Body(...),
    current_seller_id: str = Body(...),
    new_seller_id: str = Body(...),
    service: MultiAgentNegotiationService = Depends(get_multi_agent_service)
):
    """Switch a buyer from one seller to another"""
    try:
        new_negotiation_id = service.switch_seller(
            session_id=session_id,
            buyer_id=buyer_id,
            current_seller_id=current_seller_id,
            new_seller_id=new_seller_id
        )
        return {
            "message": f"Buyer {buyer_id} switched from {current_seller_id} to {new_seller_id}",
            "new_negotiation_id": new_negotiation_id
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/multi-agent/sessions/{session_id}")
def get_session_status(
    session_id: str,
    service: MultiAgentNegotiationService = Depends(get_multi_agent_service)
):
    """Get current state of all negotiations in a session"""
    try:
        session = service.get_session_status(session_id)
        return {
            "session_id": session.session_id,
            "marketplace_context": session.marketplace_context,
            "active_negotiations": [
                {
                    "negotiation_id": neg.negotiation_id,
                    "buyer_id": neg.buyer_id,
                    "seller_id": neg.seller_id,
                    "status": neg.status,
                    "turns": len(neg.turns),
                    "last_buyer_offer": neg.last_buyer_offer,
                    "last_seller_offer": neg.last_seller_offer,
                    "buyer_patience": neg.buyer_patience,
                    "seller_patience": neg.seller_patience
                }
                for neg in session.active_negotiations.values()
            ],
            "completed_negotiations": [
                {
                    "negotiation_id": neg.negotiation_id,
                    "buyer_id": neg.buyer_id,
                    "seller_id": neg.seller_id,
                    "status": neg.status,
                    "agreed": neg.agreed,
                    "final_price": neg.final_price,
                    "reason": neg.reason,
                    "turns": len(neg.turns)
                }
                for neg in session.completed_negotiations
            ]
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/multi-agent/sessions/{session_id}/negotiations/{negotiation_id}/transcript")
def get_negotiation_transcript(
    session_id: str,
    negotiation_id: str,
    service: MultiAgentNegotiationService = Depends(get_multi_agent_service)
):
    """Get full transcript of a specific negotiation"""
    try:
        session = service.get_session_status(session_id)
        
        # Search in active negotiations
        negotiation = session.active_negotiations.get(negotiation_id)
        if not negotiation:
            # Search in completed negotiations
            for completed in session.completed_negotiations:
                if completed.negotiation_id == negotiation_id:
                    negotiation = completed
                    break
        
        if not negotiation:
            raise HTTPException(status_code=404, detail=f"Negotiation {negotiation_id} not found")
        
        return {
            "negotiation_id": negotiation.negotiation_id,
            "buyer_id": negotiation.buyer_id,
            "seller_id": negotiation.seller_id,
            "status": negotiation.status,
            "agreed": negotiation.agreed,
            "final_price": negotiation.final_price,
            "reason": negotiation.reason,
            "turns": [
                {
                    "round": turn.round,
                    "agent_id": turn.agent_id,
                    "agent_role": turn.agent_role,
                    "offer": turn.offer,
                    "message": turn.message
                }
                for turn in negotiation.turns
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/multi-agent/sessions/{session_id}/add-seller-interest")
def add_seller_to_buyer_interests(
    session_id: str,
    buyer_id: str = Body(...),
    seller_id: str = Body(...),
    service: MultiAgentNegotiationService = Depends(get_multi_agent_service)
):
    """Add a seller to a buyer's interest list"""
    try:
        service.add_seller_to_buyer_interests(session_id, buyer_id, seller_id)
        return {
            "message": f"Added seller {seller_id} to buyer {buyer_id}'s interests",
            "buyer_id": buyer_id,
            "seller_id": seller_id
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/multi-agent/sessions/{session_id}/automate")
def automate_session(
    session_id: str,
    request: AutomateSessionRequest = Body(...),
    service: MultiAgentNegotiationService = Depends(get_multi_agent_service)
):
    """
    Execute entire session automatically with agent autonomy.
    Buyers will negotiate with their interested sellers and can switch autonomously.
    Once a deal is made, both buyer and seller become inactive.
    """
    try:
        results = service.execute_automated_session(
            session_id=session_id,
            max_rounds_per_negotiation=request.max_rounds_per_negotiation,
            allow_agent_switching=request.allow_agent_switching
        )
        return {
            "session_id": session_id,
            "summary": {
                "total_deals": len(results["deals_made"]),
                "total_deadlocks": len(results["deadlocks"]),
                "total_switches": len(results["switches"]),
                "total_rounds": results["total_rounds"]
            },
            "deals": results["deals_made"],
            "deadlocks": results["deadlocks"],
            "switches": results["switches"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search", response_model=SearchResponse)
def search_products(
    request: SearchRequest = Body(
        ...,
        example={
            "query": "I need a gaming laptop with at least 16GB RAM under $1500",
            "user_budget": 1500.0,
            "top_k": 5,
            "use_vector": True
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
                        "parsed_query": parsed.dict() if hasattr(parsed, "dict") else None,
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
                        "data": response.dict(),
                        "suggestion": suggestion,
                    })
                elif len(response.results) < 3:
                    suggestion = await run_in_threadpool(generate_refinement_suggestion, parsed, "few_results")
                    await websocket.send_json({
                        "type": "search_results",
                        "data": response.dict(),
                        "suggestion": suggestion,
                    })
                else:
                    await websocket.send_json({
                        "type": "search_results",
                        "data": response.dict(),
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
                    "data": response.dict(),
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
                    "data": neg_result.dict(),
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

@app.websocket("/ws/negotiations/{listing_id}")
async def negotiations_ws(websocket: WebSocket, listing_id: int):
    await websocket.accept()
    room = _room_for_listing(listing_id)

    # Join message
    try:
        join_raw = await websocket.receive_text()
        join_msg = json.loads(join_raw)
    except Exception:
        await websocket.send_json({"type": "error", "message": "Invalid join payload"})
        await websocket.close()
        return

    role = join_msg.get("role")
    name = join_msg.get("name") or role
    if role not in {"buyer", "seller"}:
        await websocket.send_json({"type": "error", "message": "role must be buyer or seller"})
        await websocket.close()
        return

    if role == "buyer":
        room["buyers"].add(websocket)
        room["buyer_delegate"] = bool(join_msg.get("delegate"))
        if join_msg.get("counterparty") == "agent":
            room["seller_delegate"] = True
        buyer_max = join_msg.get("buyer_max_price")
        if buyer_max:
            room["buyer_max_price"] = float(buyer_max)
    else:
        room["sellers"].add(websocket)
        room["seller_delegate"] = bool(join_msg.get("delegate"))
        if join_msg.get("counterparty") == "agent":
            room["buyer_delegate"] = True
        seller_min = join_msg.get("seller_min_price")
        if seller_min:
            room["seller_min_price"] = float(seller_min)

    # Load listing for agent replies
    listing = None
    db = SessionLocal()
    try:
        listing = db.query(Listing).filter(Listing.id == listing_id).first()
    finally:
        db.close()

    await websocket.send_json({"type": "state", "turns": room["turns"]})

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            if msg.get("type") != "offer":
                await websocket.send_json({"type": "error", "message": "Unknown message type"})
                continue

            offer = msg.get("offer")
            message = msg.get("message", "")
            if offer is None:
                await websocket.send_json({"type": "error", "message": "Offer is required"})
                continue

            turn = {
                "round": len(room["turns"]) + 1,
                "agent": role,
                "offer": float(offer),
                "message": message,
                "name": name,
            }
            room["turns"].append(turn)

            # Broadcast turn
            for ws in list(room["buyers"] | room["sellers"]):
                await ws.send_json({"type": "turn", "turn": turn})

            # Agent response if enabled
            if role == "buyer" and room["seller_delegate"] and listing:
                agent = SellerAgent(
                    float(room["seller_min_price"] or (listing.price * 0.8))
                )
                context = _build_context(room["turns"])
                offer_data = agent.propose(
                    context,
                    float(offer),
                    rounds_left=5,
                    market_context=f"You have medium leverage. (Demand: {len(room['buyers'])} interested buyers).",
                    product_description=listing.description or listing.title,
                )
                seller_turn = {
                    "round": len(room["turns"]) + 1,
                    "agent": "seller",
                    "offer": float(offer_data["offer"]),
                    "message": offer_data["message"],
                    "name": "Seller",
                }
                room["turns"].append(seller_turn)
                for ws in list(room["buyers"] | room["sellers"]):
                    await ws.send_json({"type": "turn", "turn": seller_turn})

            if role == "seller" and room["buyer_delegate"] and listing:
                buyer_max = room["buyer_max_price"] or float(listing.price)
                agent = BuyerAgent(float(buyer_max))
                context = _build_context(room["turns"])
                offer_data = agent.propose(
                    context,
                    float(offer),
                    rounds_left=5,
                    market_context=f"You have medium leverage. (Competition: {len(room['sellers'])} other sellers).",
                    product_description=listing.description or listing.title,
                )
                buyer_turn = {
                    "round": len(room["turns"]) + 1,
                    "agent": "buyer",
                    "offer": float(offer_data["offer"]),
                    "message": offer_data["message"],
                    "name": "Buyer",
                }
                room["turns"].append(buyer_turn)
                for ws in list(room["buyers"] | room["sellers"]):
                    await ws.send_json({"type": "turn", "turn": buyer_turn})

    except WebSocketDisconnect:
        pass
    finally:
        if role == "buyer":
            room["buyers"].discard(websocket)
        else:
            room["sellers"].discard(websocket)

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