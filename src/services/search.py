import json
import math
import re
import threading
from typing import Dict, List, Optional, Tuple

from openai import OpenAI
from sqlalchemy.orm import Session

from src.config import settings
from src.models.db_models import Listing
from src.models.schemas import (
    ListingOut,
    ParsedQuery,
    SearchRequest,
    SearchResponse,
    SearchResult,
)


class SearchService:
    """Search copilot service.

    - Parses natural language into a ParsedQuery (LLM)
    - Ranks listings using OpenAI embeddings cosine similarity (cheap model)
    - Applies optional budget filtering

    Notes:
    - For this PoC we keep an in-memory embedding cache keyed by listing_id.
    - If listings change, call `refresh_index(db)` (we also refresh lazily).
    """

    # OpenAI embedding model - using a smaller, cheaper model for this use case since we just need general semantic similarity for product listings.
    EMBEDDING_MODEL = "text-embedding-3-small"

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self._lock = threading.Lock()
        self._emb_cache: Dict[int, List[float]] = {}
        self._cache_count: int = 0

    # -----------------------------
    # LLM parsing
    # -----------------------------
    def parse_query(self, query: str, user_budget: Optional[float] = None) -> ParsedQuery:
        system = (
            "You extract structured shopping intent from a user query. "
            "Return ONLY valid JSON with these keys: "
            "product_type (string or null), description (string or null), "
            "max_budget (number or null), min_budget (number or null), "
            "category (string or null), parse_confidence (number 0..1)."
        )

        user = {
            "query": query,
            "user_budget": user_budget,
            "instructions": "If a budget is present in the query, set max_budget. If user_budget is provided, prefer it as max_budget.",
        }

        resp = self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user)},
            ],
            temperature=0.1,
            max_tokens=200,
        )

        content = (resp.choices[0].message.content or "").strip()

        # Best case: pure JSON
        try:
            data = json.loads(content)
            # Prefer explicit user_budget override
            if user_budget is not None:
                data["max_budget"] = float(user_budget)
            return ParsedQuery(**data)
        except Exception:
            pass

        # Fallback: extract JSON blob
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0))
                if user_budget is not None:
                    data["max_budget"] = float(user_budget)
                return ParsedQuery(**data)
            except Exception:
                pass

        # Final fallback: very basic budget extraction from text
        max_b = None
        budget_match = re.search(r"\$\s*(\d+(?:\.\d+)?)", query)
        if budget_match:
            try:
                max_b = float(budget_match.group(1))
            except Exception:
                max_b = None
        if user_budget is not None:
            max_b = float(user_budget)

        return ParsedQuery(
            product_type=None,
            description=None,
            max_budget=max_b,
            min_budget=None,
            category=None,
            parse_confidence=0.2,
        )

    # -----------------------------
    # Embeddings helpers
    # -----------------------------
    def _embed_text(self, text: str) -> List[float]:
        text = (text or "").strip()
        if not text:
            # return a tiny vector; caller should handle empty gracefully
            return [0.0]

        emb = self.client.embeddings.create(
            model=self.EMBEDDING_MODEL,
            input=text,
        )
        return emb.data[0].embedding

    @staticmethod
    def _cosine(a: List[float], b: List[float]) -> float:
        # Handle degenerate cases
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = 0.0
        na = 0.0
        nb = 0.0
        for x, y in zip(a, b):
            dot += x * y
            na += x * x
            nb += y * y
        if na == 0.0 or nb == 0.0:
            return 0.0
        return dot / (math.sqrt(na) * math.sqrt(nb))

    def refresh_index(self, db: Session) -> None:
        """Build/refresh the in-memory embedding cache for all listings."""
        listings = db.query(Listing).all()
        with self._lock:
            self._emb_cache = {}
            self._cache_count = 0

        for l in listings:
            text = f"{l.title or ''}\n{l.description or ''}".strip()
            vec = self._embed_text(text)
            with self._lock:
                self._emb_cache[int(l.id)] = vec
                self._cache_count += 1

    def _ensure_index(self, db: Session) -> None:
        """Lazy index build: if the number of cached embeddings doesn't match listing count, rebuild."""
        count = db.query(Listing).count()
        with self._lock:
            cached = self._cache_count
        if cached != count:
            self.refresh_index(db)

    # -----------------------------
    # Search
    # -----------------------------
    def search_listings(self, parsed: ParsedQuery, db: Session, top_k: int = 5, use_vector: bool = True) -> List[SearchResult]:
        self._ensure_index(db)

        # Budget logic: prefer parsed.max_budget; if missing, no budget filter
        max_budget = parsed.max_budget
        min_budget = parsed.min_budget

        # Query base (optional hard filters)
        q = db.query(Listing)
        if parsed.category:
            q = q.filter(Listing.category.ilike(f"%{parsed.category}%"))
        if max_budget is not None:
            q = q.filter(Listing.price <= max_budget)
        if min_budget is not None:
            q = q.filter(Listing.price >= min_budget)

        candidates = q.all()

        # If vector search disabled, fallback to simple keyword match ordering
        if not use_vector:
            term = (parsed.product_type or "").strip().lower()
            results: List[SearchResult] = []
            for l in candidates:
                title = (l.title or "").lower()
                desc = (l.description or "").lower()
                score = 0.5
                reasons: List[str] = []
                if term and term in title:
                    score = 1.0
                    reasons.append("Matches product type")
                if max_budget is not None:
                    reasons.append("Within budget")
                results.append(
                    SearchResult(
                        listing=ListingOut.from_orm(l),
                        relevance_score=float(score),
                        reasons=reasons,
                        negotiation_ready=(max_budget is not None and float(l.price) <= float(max_budget)),
                    )
                )
            results.sort(key=lambda r: r.relevance_score, reverse=True)
            return results[:top_k]

        # Vector query text = product_type + description + original query (if available)
        query_text_parts = [parsed.product_type or "", parsed.description or ""]
        query_text = " ".join([p for p in query_text_parts if p]).strip()
        if not query_text:
            # no parse info; just use a neutral query
            query_text = "product"

        q_vec = self._embed_text(query_text)

        scored: List[Tuple[float, Listing, List[str]]] = []
        for l in candidates:
            with self._lock:
                l_vec = self._emb_cache.get(int(l.id))
            if not l_vec or len(l_vec) != len(q_vec):
                # compute on the fly (and cache)
                text = f"{l.title or ''}\n{l.description or ''}".strip()
                l_vec = self._embed_text(text)
                with self._lock:
                    self._emb_cache[int(l.id)] = l_vec
                    self._cache_count = max(self._cache_count, len(self._emb_cache))

            sim = self._cosine(q_vec, l_vec)
            reasons: List[str] = ["Semantic match"]

            # Light budget preference (within budget gets a small bump)
            if max_budget is not None:
                if float(l.price) <= float(max_budget):
                    sim = min(1.0, sim + 0.05)
                    reasons.append("Within budget")
                else:
                    reasons.append("Over budget")

            scored.append((sim, l, reasons))

        scored.sort(key=lambda t: t[0], reverse=True)

        # Normalize similarity into 0..1 (cosine is already roughly in that range, but clamp)
        results: List[SearchResult] = []
        for sim, l, reasons in scored[:top_k]:
            sim_clamped = float(max(0.0, min(1.0, sim)))
            results.append(
                SearchResult(
                    listing=ListingOut.from_orm(l),
                    relevance_score=sim_clamped,
                    reasons=reasons,
                    negotiation_ready=(max_budget is not None and float(l.price) <= float(max_budget)),
                )
            )

        return results

    def perform_search(self, request: SearchRequest, db: Session) -> SearchResponse:
        parsed = self.parse_query(request.query, request.user_budget)

        # Ensure max_budget uses user_budget override if present
        if request.user_budget is not None:
            parsed.max_budget = float(request.user_budget)

        results = self.search_listings(
            parsed=parsed,
            db=db,
            top_k=request.top_k,
            use_vector=request.use_vector,
        )

        budget_txt = f" under ${parsed.max_budget}" if parsed.max_budget is not None else ""
        topic = parsed.product_type or "results"
        message = f"Found {len(results)} matches for '{topic}'{budget_txt}."

        return SearchResponse(
            parsed_query=parsed,
            results=results,
            message=message,
        )