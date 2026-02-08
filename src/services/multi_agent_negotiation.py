"""
Multi-Agent Negotiation Service
Manages multiple concurrent buyer-seller negotiations with marketplace visibility
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from src.agents.seller import SellerAgent
from src.agents.buyer import BuyerAgent
from src.models.schemas import (
    MultiAgentSession,
    NegotiationState,
    MultiAgentNegotiationTurn,
    MarketplaceContext,
    BuyerConfig,
    SellerConfig,
    CreateSessionRequest,
    Product
)
from src.models.db_models import Listing
from src.repositories import SessionRepository


class MultiAgentNegotiationService:
    """Manages multiple concurrent 1-1 negotiations in a free market"""
    
    def __init__(self, repository: SessionRepository, db: Session = None):
        self.repository = repository
        self.db = db
        self._agent_cache: Dict[str, tuple] = {}  # agent_id -> (agent_instance, config)
    
    def create_session(self, request: CreateSessionRequest) -> MultiAgentSession:
        """Initialize a multi-agent negotiation session"""
        session_id = str(uuid.uuid4())
        
        # Collect listing IDs
        listing_ids = list(set(s.listing_id for s in request.sellers))
        
        # Build buyer and seller config maps
        buyers = {b.agent_id: b for b in request.buyers}
        sellers = {s.agent_id: s for s in request.sellers}
        
        # Initialize marketplace context
        marketplace_context = MarketplaceContext(
            total_active_buyers=len(buyers),
            total_active_sellers=len(sellers),
            active_negotiations_count=0,
            recent_completed_prices=[]
        )
        
        session = MultiAgentSession(
            session_id=session_id,
            listing_ids=listing_ids,
            buyers=buyers,
            sellers=sellers,
            active_negotiations={},
            completed_negotiations=[],
            marketplace_context=marketplace_context,
            created_at=datetime.now().isoformat()
        )
        
        self.repository.create_session(session)
        return session
    
    def start_negotiation(
        self,
        session_id: str,
        buyer_id: str,
        seller_id: str
    ) -> NegotiationState:
        """Start a new 1-1 negotiation between a buyer and seller"""
        session = self.repository.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if buyer_id not in session.buyers:
            raise ValueError(f"Buyer {buyer_id} not in session")
        if seller_id not in session.sellers:
            raise ValueError(f"Seller {seller_id} not in session")
        
        buyer_config = session.buyers[buyer_id]
        seller_config = session.sellers[seller_id]
        
        # Check if buyer/seller are still active (haven't made deals yet)
        if not buyer_config.active:
            raise ValueError(f"Buyer {buyer_id} is inactive (already made a deal)")
        if not seller_config.active:
            raise ValueError(f"Seller {seller_id} is inactive (already sold the product)")
        
        # Check if buyer is interested in this seller
        if buyer_config.interested_seller_ids and seller_id not in buyer_config.interested_seller_ids:
            raise ValueError(f"Buyer {buyer_id} is not interested in seller {seller_id}. Use add_seller_to_buyer_interests() first.")
        
        # Check if this buyer is already negotiating with this seller
        for neg in session.active_negotiations.values():
            if neg.buyer_id == buyer_id and neg.seller_id == seller_id:
                raise ValueError(f"Negotiation already active between {buyer_id} and {seller_id}")
        
        buyer_config = session.buyers[buyer_id]
        seller_config = session.sellers[seller_id]
        
        # Get product info
        product_info = self._get_product_info(seller_config.listing_id)
        
        # Calculate leverage
        buyer_leverage = self._calculate_buyer_leverage(session, buyer_id)
        seller_leverage = self._calculate_seller_leverage(session, seller_id)
        
        # Calculate patience
        buyer_patience = buyer_config.patience or self._calculate_initial_patience(buyer_leverage)
        seller_patience = seller_config.patience or self._calculate_initial_patience(seller_leverage)
        
        # Calculate seller target
        seller_target = self._calculate_seller_target(
            seller_config.min_price,
            seller_config.listing_price,
            seller_leverage
        )
        
        # Create negotiation
        negotiation_id = f"{buyer_id}_{seller_id}_{str(uuid.uuid4())[:8]}"
        negotiation = NegotiationState(
            negotiation_id=negotiation_id,
            buyer_id=buyer_id,
            seller_id=seller_id,
            buyer_patience=buyer_patience,
            seller_patience=seller_patience,
            buyer_leverage=buyer_leverage,
            seller_leverage=seller_leverage,
            seller_target=seller_target,
            turns=[],
            status="active"
        )
        
        # Add to session
        self.repository.add_negotiation(session_id, negotiation)
        
        # Update marketplace context
        session = self.repository.get_session(session_id)
        session.marketplace_context.active_negotiations_count = len(session.active_negotiations)
        self.repository.update_session(session)
        
        return negotiation
    
    def execute_turn(
        self,
        session_id: str,
        negotiation_id: str
    ) -> MultiAgentNegotiationTurn:
        """Execute one turn in a specific negotiation"""
        session = self.repository.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        negotiation = session.active_negotiations.get(negotiation_id)
        if not negotiation:
            raise ValueError(f"Negotiation {negotiation_id} not found or already completed")
        
        # Determine whose turn it is
        if not negotiation.turns:
            # First turn: buyer responds to listing price
            agent_turn = "buyer"
            last_offer = session.sellers[negotiation.seller_id].listing_price
        else:
            last_turn = negotiation.turns[-1]
            agent_turn = "seller" if last_turn.agent_role == "buyer" else "buyer"
            last_offer = last_turn.offer
        
        # Get or create agents
        if agent_turn == "buyer":
            agent_id = negotiation.buyer_id
            agent = self._get_or_create_buyer_agent(session, agent_id)
            counterparty_id = negotiation.seller_id
            patience_left = negotiation.buyer_patience
        else:
            agent_id = negotiation.seller_id
            agent = self._get_or_create_seller_agent(session, agent_id)
            counterparty_id = negotiation.buyer_id
            patience_left = negotiation.seller_patience
        
        # Build context and histories
        context = self._build_context_string(negotiation.turns, agent_id)
        own_offer_history = [t.offer for t in negotiation.turns if t.agent_id == agent_id]
        counterparty_offer_history = [(t.agent_id, t.offer) for t in negotiation.turns if t.agent_id != agent_id]
        
        # Get market context
        market_context = self._build_market_context_string(session, agent_id, agent_turn)
        
        # Get product description
        seller_id = negotiation.seller_id
        product_info = self._get_product_info(session.sellers[seller_id].listing_id)
        product_desc = product_info.get("description", product_info.get("name", ""))
        
        # Make proposal
        offer_data = agent.propose_structured(
            context=context,
            counterparty_last_offer=last_offer,
            own_offer_history=own_offer_history,
            counterparty_offer_history=counterparty_offer_history,
            rounds_left=patience_left,
            market_context=market_context,
            product_description=product_desc
        )
        
        offer = offer_data["offer"]
        message = offer_data["message"]
        round_num = len(negotiation.turns) + 1
        
        # Create turn
        turn = MultiAgentNegotiationTurn(
            round=round_num,
            negotiation_id=negotiation_id,
            agent_id=agent_id,
            agent_role=agent_turn,
            offer=offer,
            message=message
        )
        
        negotiation.turns.append(turn)
        
        # Update stall tracking
        if agent_turn == "buyer":
            if negotiation.last_buyer_offer is not None and abs(offer - negotiation.last_buyer_offer) < 0.01:
                negotiation.buyer_stall_count += 1
            else:
                negotiation.buyer_stall_count = 0
            negotiation.last_buyer_offer = offer
        else:
            if negotiation.last_seller_offer is not None and abs(offer - negotiation.last_seller_offer) < 0.01:
                negotiation.seller_stall_count += 1
            else:
                negotiation.seller_stall_count = 0
            negotiation.last_seller_offer = offer
        
        # Check for agreement
        if abs(offer - last_offer) < 0.01:
            negotiation.agreed = True
            negotiation.final_price = offer
            negotiation.status = "agreed"
            negotiation.reason = f"{agent_turn.capitalize()} accepted the offer."
            # Mark both agents as inactive since deal is made
            self._mark_agents_inactive_after_deal(session_id, negotiation.buyer_id, negotiation.seller_id)
        
        # Check for stall (both parties stuck for 2+ rounds)
        elif negotiation.buyer_stall_count >= 2 and negotiation.seller_stall_count >= 2:
            # Calculate midpoint
            buyer_config = session.buyers[negotiation.buyer_id]
            seller_config = session.sellers[negotiation.seller_id]
            
            if seller_config.min_price <= buyer_config.max_price:
                midpoint = (negotiation.last_buyer_offer + negotiation.last_seller_offer) / 2
                final_offer = min(max(midpoint, seller_config.min_price), buyer_config.max_price)
                
                system_turn = MultiAgentNegotiationTurn(
                    round=round_num + 1,
                    negotiation_id=negotiation_id,
                    agent_id="system",
                    agent_role="system",
                    offer=final_offer,
                    message="Final offer to conclude the negotiation. Both parties have reached their positions."
                )
                negotiation.turns.append(system_turn)
                negotiation.agreed = True
                negotiation.final_price = final_offer
                negotiation.status = "agreed"
                negotiation.reason = "Final offer invoked after both parties stalled."
                # Mark both agents as inactive since deal is made
                self._mark_agents_inactive_after_deal(session_id, negotiation.buyer_id, negotiation.seller_id)
            else:
                negotiation.agreed = False
                negotiation.status = "deadlocked"
                negotiation.reason = "Non-overlapping constraints."
        
        # Decrease patience
        if agent_turn == "buyer":
            negotiation.buyer_patience -= 1
        else:
            negotiation.seller_patience -= 1
        
        # Check if patience exhausted
        if negotiation.buyer_patience <= 0 or negotiation.seller_patience <= 0:
            if negotiation.status == "active":
                negotiation.status = "deadlocked"
                negotiation.reason = "Patience exhausted."
        
        # Update negotiation
        self.repository.update_negotiation(session_id, negotiation)
        
        # If completed, update marketplace context
        if negotiation.status in ["agreed", "deadlocked"]:
            session = self.repository.get_session(session_id)
            session.marketplace_context.active_negotiations_count = len(session.active_negotiations)
            if negotiation.agreed and negotiation.final_price:
                session.marketplace_context.recent_completed_prices.append(negotiation.final_price)
            self.repository.update_session(session)
        
        return turn
    
    def switch_seller(
        self,
        session_id: str,
        buyer_id: str,
        current_seller_id: str,
        new_seller_id: str
    ) -> str:
        """Switch a buyer from one seller to another"""
        session = self.repository.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Find and end current negotiation
        for neg_id, neg in list(session.active_negotiations.items()):
            if neg.buyer_id == buyer_id and neg.seller_id == current_seller_id:
                neg.status = "switched"
                neg.reason = f"Buyer switched to seller {new_seller_id}"
                self.repository.update_negotiation(session_id, neg)
                break
        
        # Start new negotiation with new seller
        new_negotiation = self.start_negotiation(session_id, buyer_id, new_seller_id)
        return new_negotiation.negotiation_id
    
    def get_session_status(self, session_id: str) -> MultiAgentSession:
        """Get current state of all negotiations in a session"""
        session = self.repository.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        return session
    
    # Helper methods
    
    def _get_or_create_buyer_agent(self, session: MultiAgentSession, buyer_id: str) -> BuyerAgent:
        """Get or create a buyer agent instance"""
        if buyer_id in self._agent_cache:
            return self._agent_cache[buyer_id][0]
        
        config = session.buyers[buyer_id]
        agent = BuyerAgent(max_price=config.max_price, agent_id=buyer_id)
        self._agent_cache[buyer_id] = (agent, config)
        return agent
    
    def _get_or_create_seller_agent(self, session: MultiAgentSession, seller_id: str) -> SellerAgent:
        """Get or create a seller agent instance"""
        if seller_id in self._agent_cache:
            return self._agent_cache[seller_id][0]
        
        config = session.sellers[seller_id]
        agent = SellerAgent(min_price=config.min_price, agent_id=seller_id)
        self._agent_cache[seller_id] = (agent, config)
        return agent
    
    def _build_context_string(self, turns: List[MultiAgentNegotiationTurn], agent_id: str) -> str:
        """Build narrative context with agent IDs"""
        lines = []
        for turn in turns:
            marker = "You" if turn.agent_id == agent_id else turn.agent_id
            lines.append(f"{marker} ({turn.agent_role}) offered ${turn.offer}: {turn.message}")
        return "\n".join(lines)
    
    def _build_market_context_string(self, session: MultiAgentSession, agent_id: str, role: str) -> str:
        """Build market context string with competitive info"""
        mc = session.marketplace_context
        
        if role == "buyer":
            leverage = self._calculate_buyer_leverage(session, agent_id)
            return (
                f"You have {leverage} leverage. "
                f"Market: {mc.total_active_sellers} sellers available, {mc.total_active_buyers} total buyers competing. "
                f"Active negotiations: {mc.active_negotiations_count}. "
            )
        else:
            leverage = self._calculate_seller_leverage(session, agent_id)
            return (
                f"You have {leverage} leverage. "
                f"Market: {mc.total_active_buyers} buyers interested, {mc.total_active_sellers} total sellers competing. "
                f"Active negotiations: {mc.active_negotiations_count}. "
            )
    
    def _calculate_buyer_leverage(self, session: MultiAgentSession, buyer_id: str) -> str:
        """Calculate buyer leverage based on market supply"""
        # Buyer leverage = High Supply (More Sellers)
        seller_count = session.marketplace_context.total_active_sellers
        if seller_count >= 3:
            return "high"
        elif seller_count == 1:
            return "low"
        return "medium"
    
    def _calculate_seller_leverage(self, session: MultiAgentSession, seller_id: str) -> str:
        """Calculate seller leverage based on market demand"""
        # Seller leverage = High Demand (More Buyers)
        buyer_count = session.marketplace_context.total_active_buyers
        if buyer_count >= 3:
            return "high"
        elif buyer_count == 1:
            return "low"
        return "medium"
    
    def _calculate_initial_patience(self, leverage: str) -> int:
        """Determine initial patience rounds based on leverage"""
        if leverage == "high":
            return 6  # Confident, less willing to wait
        elif leverage == "low":
            return 15  # Desperate, willing to grind
        else:
            return 10  # Balanced
    
    def _calculate_seller_target(self, min_price: float, listing_price: float, leverage: str) -> float:
        """Calculate seller's internal target price"""
        if leverage == "high":
            k = 0.85
        elif leverage == "medium":
            k = 0.60
        else:  # low
            k = 0.35
        
        target = min_price + (listing_price - min_price) * k
        return max(min_price, min(target, listing_price))
    
    def _get_product_info(self, listing_id: int) -> dict:
        """Get product information from database"""
        if not self.db:
            return {"name": "Product", "description": ""}
        
        listing = self.db.query(Listing).filter(Listing.id == listing_id).first()
        if not listing:
            return {"name": "Product", "description": ""}
        
        return {
            "name": listing.title,
            "description": listing.description or listing.title,
            "listing_price": float(listing.price)
        }
    
    def add_seller_to_buyer_interests(
        self,
        session_id: str,
        buyer_id: str,
        seller_id: str
    ) -> None:
        """Allow buyer to add a seller to their interest list"""
        session = self.repository.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if buyer_id not in session.buyers:
            raise ValueError(f"Buyer {buyer_id} not in session")
        if seller_id not in session.sellers:
            raise ValueError(f"Seller {seller_id} not in session")
        
        buyer_config = session.buyers[buyer_id]
        if seller_id not in buyer_config.interested_seller_ids:
            buyer_config.interested_seller_ids.append(seller_id)
            self.repository.update_session(session)
    
    def _mark_agents_inactive_after_deal(
        self,
        session_id: str,
        buyer_id: str,
        seller_id: str
    ) -> None:
        """Mark buyer and seller as inactive after they make a deal"""
        session = self.repository.get_session(session_id)
        if not session:
            return
        
        # Mark buyer and seller as inactive
        if buyer_id in session.buyers:
            session.buyers[buyer_id].active = False
        if seller_id in session.sellers:
            session.sellers[seller_id].active = False
        
        # Update marketplace context to reflect active counts
        session.marketplace_context.total_active_buyers = sum(1 for b in session.buyers.values() if b.active)
        session.marketplace_context.total_active_sellers = sum(1 for s in session.sellers.values() if s.active)
        
        self.repository.update_session(session)
    
    def execute_automated_session(
        self,
        session_id: str,
        max_rounds_per_negotiation: int = 20,
        allow_agent_switching: bool = True
    ) -> Dict[str, any]:
        """
        Execute an entire session automatically with agent autonomy.
        
        Args:
            session_id: Session to run
            max_rounds_per_negotiation: Max turns per negotiation before giving up
            allow_agent_switching: Allow buyer agents to switch sellers autonomously
            
        Returns:
            Summary of all negotiations and outcomes
        """
        session = self.repository.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        results = {
            "session_id": session_id,
            "deals_made": [],
            "deadlocks": [],
            "switches": [],
            "total_rounds": 0
        }
        
        # Start negotiation for each buyer with their first interested seller
        for buyer_id, buyer_config in session.buyers.items():
            if not buyer_config.active:
                continue
                
            if not buyer_config.interested_seller_ids:
                continue
            
            # Start with first interested seller
            seller_id = buyer_config.interested_seller_ids[0]
            seller_config = session.sellers.get(seller_id)
            
            if not seller_config or not seller_config.active:
                continue
            
            try:
                negotiation = self.start_negotiation(session_id, buyer_id, seller_id)
                current_neg_id = negotiation.negotiation_id
                
                # Run negotiation loop
                while True:
                    session = self.repository.get_session(session_id)
                    negotiation = session.active_negotiations.get(current_neg_id)
                    
                    if not negotiation or negotiation.status != "active":
                        break
                    
                    # Check if we've exceeded max rounds
                    if len(negotiation.turns) >= max_rounds_per_negotiation:
                        negotiation.status = "deadlocked"
                        negotiation.reason = "Max rounds exceeded"
                        self.repository.update_negotiation(session_id, negotiation)
                        results["deadlocks"].append({
                            "buyer_id": buyer_id,
                            "seller_id": negotiation.seller_id,
                            "rounds": len(negotiation.turns),
                            "reason": "Max rounds exceeded"
                        })
                        break
                    
                    # Execute one turn
                    turn = self.execute_turn(session_id, current_neg_id)
                    results["total_rounds"] += 1
                    
                    # Refresh negotiation state
                    session = self.repository.get_session(session_id)
                    negotiation = session.active_negotiations.get(current_neg_id)
                    
                    if not negotiation:
                        # Negotiation completed
                        completed = next((n for n in session.completed_negotiations if n.negotiation_id == current_neg_id), None)
                        if completed:
                            if completed.agreed:
                                results["deals_made"].append({
                                    "buyer_id": buyer_id,
                                    "seller_id": completed.seller_id,
                                    "final_price": completed.final_price,
                                    "rounds": len(completed.turns)
                                })
                                # Mark agents as inactive
                                self._mark_agents_inactive_after_deal(session_id, buyer_id, completed.seller_id)
                            elif completed.status == "deadlocked":
                                results["deadlocks"].append({
                                    "buyer_id": buyer_id,
                                    "seller_id": completed.seller_id,
                                    "rounds": len(completed.turns),
                                    "reason": completed.reason
                                })
                        break
                    
                    # Check if buyer agent wants to switch (if enabled)
                    if allow_agent_switching and negotiation.status == "active":
                        buyer_agent = self._get_or_create_buyer_agent(session, buyer_id)
                        
                        # Get buyer's offer history
                        buyer_offers = [t.offer for t in negotiation.turns if t.agent_role == "buyer"]
                        seller_offers = [t.offer for t in negotiation.turns if t.agent_role == "seller"]
                        
                        # Get available alternative sellers
                        available_sellers = [
                            sid for sid in buyer_config.interested_seller_ids
                            if sid != negotiation.seller_id and session.sellers[sid].active
                        ]
                        
                        should_switch = buyer_agent.should_switch_seller(
                            own_offer_history=buyer_offers,
                            counterparty_offer_history=seller_offers,
                            stall_count=negotiation.buyer_stall_count,
                            rounds_left=negotiation.buyer_patience - len([t for t in negotiation.turns if t.agent_role == "buyer"]),
                            has_alternatives=len(available_sellers) > 0
                        )
                        
                        if should_switch and available_sellers:
                            # Switch to next available seller
                            new_seller_id = available_sellers[0]
                            
                            # Mark negotiation as switched
                            negotiation.status = "switched"
                            negotiation.reason = f"Buyer autonomously switched to {new_seller_id}"
                            self.repository.update_negotiation(session_id, negotiation)
                            
                            results["switches"].append({
                                "buyer_id": buyer_id,
                                "from_seller": negotiation.seller_id,
                                "to_seller": new_seller_id,
                                "rounds_before_switch": len(negotiation.turns)
                            })
                            
                            # Start new negotiation
                            new_neg = self.start_negotiation(session_id, buyer_id, new_seller_id)
                            current_neg_id = new_neg.negotiation_id
            
            except Exception as e:
                # Log error but continue with other buyers
                results["deadlocks"].append({
                    "buyer_id": buyer_id,
                    "seller_id": seller_id if 'seller_id' in locals() else "unknown",
                    "rounds": 0,
                    "reason": f"Error: {str(e)}"
                })
        
        return results
