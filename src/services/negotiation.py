from typing import Callable
from src.agents.seller import SellerAgent
from src.agents.buyer import BuyerAgent
from src.models.schemas import NegotiationRequest, NegotiationTurn, NegotiationResult

class NegotiationService:
    def __init__(self):
        pass

    def _calculate_initial_patience(self, leverage: str) -> int:
        """Determines initial patience rounds based on leverage."""
        if leverage == "high":
            return 6  # Confident, less willing to wait (Aggressive)
        elif leverage == "low":
            return 15 # Desperate, willing to grind (Patient)
        else:
            return 10 # Balanced

    def _determine_leverage(self, role: str, req: NegotiationRequest) -> str:
        if role == "seller":
            # Seller Leverage = High Demand (More Buyers)
            if req.active_interested_buyers >= 3:
                return "high"
            elif req.active_interested_buyers == 0:
                return "low"
            return "medium"
        else:
            # Buyer Leverage = High Supply (More Sellers)
            if req.active_competitor_sellers >= 3:
                return "high"
            elif req.active_competitor_sellers == 0:
                return "low"
            return "medium"

    def _max_concession(self, listing_price: float, leverage: str, rounds_left: int | None) -> float:
        if leverage == "high":
            pct = 0.01
        elif leverage == "low":
            pct = 0.06
        else:
            pct = 0.03

        if rounds_left is not None and rounds_left <= 3:
            pct *= 2

        return max(1.0, listing_price * pct)

    def negotiate(self, req: NegotiationRequest) -> NegotiationResult:
        seller = SellerAgent(req.seller_min_price)
        buyer = BuyerAgent(req.buyer_max_price)
        turns = []
        context = []
        round_num = 1
        
        # Determine Market Context
        seller_leverage = self._determine_leverage("seller", req)
        buyer_leverage = self._determine_leverage("buyer", req)
        
        # Calculate Seller Target based on Leverage
        listing = req.product.listing_price
        # k factor determines how close to listing price the seller wants to stay
        if seller_leverage == "high":
            k = 0.85
        elif seller_leverage == "medium":
            k = 0.60
        else: # low
            k = 0.35
            
        seller_target = req.seller_min_price + (listing - req.seller_min_price) * k
        seller_target = max(req.seller_min_price, min(seller_target, listing))
        
        # Patience tracking (Dynamic or Override)
        seller_patience = req.seller_patience or self._calculate_initial_patience(seller_leverage)
        buyer_patience = req.buyer_patience or self._calculate_initial_patience(buyer_leverage)
        
        seller_offer = req.initial_seller_offer or req.product.listing_price
        last_offer = seller_offer
        last_buyer_offer = None
        last_seller_offer = seller_offer
        agent_turn = "buyer" # Buyer responds to the listing price
        agreed = False
        final_price = None
        reason = None
        last_buyer_offer = None
        last_seller_offer = None
        buyer_stall_count = 0
        seller_stall_count = 0
        
        while buyer_patience > 0 and seller_patience > 0:
            if agent_turn == "buyer":
                # Pass leverage context to agent
                market_context = f"You have {buyer_leverage} leverage. (Competition: {req.active_competitor_sellers} other sellers)."
                
                # Use description if available
                desc = req.product.description if req.product.description else req.product.name
                
                offer_data = buyer.propose(context, last_offer, rounds_left=buyer_patience, market_context=market_context, product_description=desc)
                offer = offer_data.get("offer", last_offer)
                message = offer_data.get("message", "")

                if last_buyer_offer is not None:
                    max_step = self._max_concession(listing, buyer_leverage, buyer_patience)
                    max_offer = last_buyer_offer + max_step
                    if offer < last_buyer_offer:
                        offer = last_buyer_offer
                        message = f"I need to stay consistent. My offer remains at ${offer}."
                    elif offer > max_offer:
                        offer = max_offer
                        message = f"I can move a bit, but my offer is ${offer}."
                
                # Update State
                turns.append(NegotiationTurn(round=round_num, agent="buyer", offer=offer, message=message))
                context.append({"agent":"buyer","message":message})

                if last_buyer_offer is not None and abs(offer - last_buyer_offer) < 0.01:
                    buyer_stall_count += 1
                else:
                    buyer_stall_count = 0
                last_buyer_offer = offer
                
                # Check agreement
                if abs(offer - last_offer) < 0.01:
                    agreed = True
                    final_price = offer
                    reason = "Buyer accepted seller's previous offer."
                    # Force explicit acceptance message
                    turns[-1].message = f"Deal. I accept ${offer}."
                    break

                if buyer_stall_count >= 2 and seller_stall_count >= 2:
                    midpoint = None
                    if last_buyer_offer is not None and last_seller_offer is not None:
                        midpoint = (last_buyer_offer + last_seller_offer) / 2
                    else:
                        midpoint = last_offer

                    if req.seller_min_price <= req.buyer_max_price:
                        final_offer = min(max(midpoint, req.seller_min_price), req.buyer_max_price)
                        turns.append(
                            NegotiationTurn(
                                round=round_num + 1,
                                agent="system",
                                offer=final_offer,
                                message="Final offer to conclude the negotiation."
                            )
                        )
                        agreed = True
                        final_price = final_offer
                        reason = "Final offer invoked after both parties stalled."
                    else:
                        turns.append(
                            NegotiationTurn(
                                round=round_num + 1,
                                agent="system",
                                offer=last_offer,
                                message="Final offer attempt failed due to non-overlapping constraints."
                            )
                        )
                        agreed = False
                        final_price = None
                        reason = "Final offer failed due to non-overlapping constraints."
                    break
                
                # Calculate Patience Cost for THIS agent based on THEIR move
                # Did they make a meaningful concession towards the seller's last offer?
                # Actually, patience usually drains when the *other* person is annoying. 
                # But here we model "Fuel". Each turn costs 1 fuel. 
                # If the OTHER party stalled, maybe we lose more fuel?
                # For simplicity in this turn-based logic: 
                # 1. Base cost = 1
                # 2. If I (Buyer) made a tiny move (< 0.5% improvement from my previous position?), I burn more patience? 
                # Let's keep it simple: Standard decay for now, but shorter initial patience for aggressive agents simulates "low tolerance".
                
                buyer_patience -= 1
                
                last_offer = offer
                last_buyer_offer = offer
                agent_turn = "seller"
            else:
                # Pass leverage context to agent
                market_context = f"You have {seller_leverage} leverage. (Demand: {req.active_interested_buyers} interested buyers)."
                
                # Use description if available
                desc = req.product.description if req.product.description else req.product.name
                
                offer_data = seller.propose(context, last_offer, rounds_left=seller_patience, market_context=market_context, product_description=desc)
                offer = offer_data.get("offer", last_offer)
                message = offer_data.get("message", "")

                if last_seller_offer is not None:
                    max_step = self._max_concession(listing, seller_leverage, seller_patience)
                    min_offer = last_seller_offer - max_step
                    if offer > last_seller_offer:
                        offer = last_seller_offer
                        message = f"I need to stay consistent. My offer remains at ${offer}."
                    elif offer < min_offer:
                        offer = min_offer
                        message = f"I can make a small concession. My offer is ${offer}."
                    if offer < last_offer:
                        offer = last_offer
                        message = f"I can meet you at ${offer}."
                
                turns.append(NegotiationTurn(round=round_num, agent="seller", offer=offer, message=message))
                context.append({"agent":"seller","message":message})
                
                if abs(offer - last_offer) < 0.01:
                    # Seller is trying to accept. Check if it meets their target.
                    if last_offer >= seller_target:
                        agreed = True
                        final_price = offer
                        reason = "Seller accepted buyer's previous offer."
                        # Force explicit acceptance message
                        turns[-1].message = f"Deal. I accept ${offer}."
                        break
                    else:
                        # Seller tried to accept but it's below target. Override.
                        # Ensure we don't just repeat the offer (which triggers acceptance)
                        counter_offer = max(seller_target, last_offer + 1.0)
                        
                        # Update the turn and context with the forced counter-offer
                        turns[-1].offer = counter_offer
                        turns[-1].message = "I can't do that, but I can meet you here."
                        
                        # Update local variables for next loop
                        offer = counter_offer
                        last_offer = offer
                        context[-1]["message"] = f"I can't do that, but I can meet you here: ${offer}"

                        # Track stalling: if forced counter is same as previous seller offer, increment stall
                        if last_seller_offer is not None and abs(counter_offer - last_seller_offer) < 0.01:
                            seller_stall_count += 1
                        else:
                            seller_stall_count = 0
                        last_seller_offer = counter_offer
                        
                        seller_patience -= 1
                        agent_turn = "buyer"
                        round_num += 1
                        continue

                # Track stalling based on final offer (after any overrides)
                if last_seller_offer is not None and abs(offer - last_seller_offer) < 0.01:
                    seller_stall_count += 1
                else:
                    seller_stall_count = 0
                last_seller_offer = offer

                if buyer_stall_count >= 2 and seller_stall_count >= 2:
                    midpoint = None
                    if last_buyer_offer is not None and last_seller_offer is not None:
                        midpoint = (last_buyer_offer + last_seller_offer) / 2
                    else:
                        midpoint = last_offer

                    if req.seller_min_price <= req.buyer_max_price:
                        final_offer = min(max(midpoint, req.seller_min_price), req.buyer_max_price)
                        turns.append(
                            NegotiationTurn(
                                round=round_num + 1,
                                agent="system",
                                offer=final_offer,
                                message="Final offer to conclude the negotiation. Both parties have reached their positions."
                            )
                        )
                        agreed = True
                        final_price = final_offer
                        reason = "Final offer invoked after both parties stalled."
                    else:
                        turns.append(
                            NegotiationTurn(
                                round=round_num + 1,
                                agent="system",
                                offer=last_offer,
                                message="Negotiation concluded. Parties could not reach an agreement due to non-overlapping constraints."
                            )
                        )
                        agreed = False
                        final_price = None
                        reason = "Final offer failed due to non-overlapping constraints."
                    break

                seller_patience -= 1
                
                last_offer = offer
                last_seller_offer = offer
                agent_turn = "buyer"
            round_num += 1
            
        if not agreed:
            reason = "Negotiation ended without agreement (patience exhausted)."

        # Just for debugging
        with open("context_log.txt","w") as file:
            for item in context:
                file.write(f"""{item["agent"]} : {item['message'] + '\n'}""")
            
        return NegotiationResult(
            agreed=agreed,
            final_price=final_price,
            turns=turns,
            reason=reason
        )

    def negotiate_with_human(
        self,
        req: NegotiationRequest,
        human_role: str,
        human_propose: Callable[..., dict],
        on_turn: Callable[[NegotiationTurn], None] | None = None,
    ) -> NegotiationResult:
        if human_role not in {"buyer", "seller"}:
            raise ValueError("human_role must be 'buyer' or 'seller'")

        seller = None if human_role == "seller" else SellerAgent(req.seller_min_price)
        buyer = None if human_role == "buyer" else BuyerAgent(req.buyer_max_price)
        seller_is_agent = seller is not None
        buyer_is_agent = buyer is not None

        turns = []
        context = []
        round_num = 1

        seller_leverage = self._determine_leverage("seller", req)
        buyer_leverage = self._determine_leverage("buyer", req)

        listing = req.product.listing_price
        if seller_leverage == "high":
            k = 0.85
        elif seller_leverage == "medium":
            k = 0.60
        else:
            k = 0.35

        seller_target = req.seller_min_price + (listing - req.seller_min_price) * k
        seller_target = max(req.seller_min_price, min(seller_target, listing))

        seller_patience = req.seller_patience or self._calculate_initial_patience(seller_leverage)
        buyer_patience = req.buyer_patience or self._calculate_initial_patience(buyer_leverage)

        seller_offer = req.initial_seller_offer or req.product.listing_price
        last_offer = seller_offer
        last_buyer_offer = None
        last_seller_offer = seller_offer if seller_is_agent else None
        agent_turn = "buyer"
        agreed = False
        final_price = None
        reason = None

        while buyer_patience > 0 and seller_patience > 0:
            if agent_turn == "buyer":
                market_context = f"You have {buyer_leverage} leverage. (Competition: {req.active_competitor_sellers} other sellers)."
                desc = req.product.description if req.product.description else req.product.name

                if buyer_is_agent:
                    offer_data = buyer.propose(
                        context,
                        last_offer,
                        rounds_left=buyer_patience,
                        market_context=market_context,
                        product_description=desc,
                    )
                else:
                    offer_data = human_propose(
                        context,
                        last_offer,
                        rounds_left=buyer_patience,
                        market_context=market_context,
                        product_description=desc,
                    )

                offer = offer_data.get("offer", last_offer)
                message = offer_data.get("message", "")

                if buyer_is_agent and last_buyer_offer is not None:
                    max_step = self._max_concession(listing, buyer_leverage, buyer_patience)
                    max_offer = last_buyer_offer + max_step
                    if offer < last_buyer_offer:
                        offer = last_buyer_offer
                        message = f"I need to stay consistent. My offer remains at ${offer}."
                    elif offer > max_offer:
                        offer = max_offer
                        message = f"I can move a bit, but my offer is ${offer}."

                turns.append(NegotiationTurn(round=round_num, agent="buyer", offer=offer, message=message))
                if on_turn:
                    on_turn(turns[-1])
                context.append({"agent":"buyer","message":message})

                if abs(offer - last_offer) < 0.01:
                    agreed = True
                    final_price = offer
                    reason = "Buyer accepted seller's previous offer."
                    turns[-1].message = f"Deal. I accept ${offer}."
                    break

                buyer_patience -= 1
                last_offer = offer
                if buyer_is_agent:
                    last_buyer_offer = offer
                agent_turn = "seller"
            else:
                market_context = f"You have {seller_leverage} leverage. (Demand: {req.active_interested_buyers} interested buyers)."
                desc = req.product.description if req.product.description else req.product.name

                if seller_is_agent:
                    offer_data = seller.propose(
                        context,
                        last_offer,
                        rounds_left=seller_patience,
                        market_context=market_context,
                        product_description=desc,
                    )
                else:
                    offer_data = human_propose(
                        context,
                        last_offer,
                        rounds_left=seller_patience,
                        market_context=market_context,
                        product_description=desc,
                    )

                offer = offer_data.get("offer", last_offer)
                message = offer_data.get("message", "")

                if seller_is_agent and last_seller_offer is not None:
                    max_step = self._max_concession(listing, seller_leverage, seller_patience)
                    min_offer = last_seller_offer - max_step
                    if offer > last_seller_offer:
                        offer = last_seller_offer
                        message = f"I need to stay consistent. My offer remains at ${offer}."
                    elif offer < min_offer:
                        offer = min_offer
                        message = f"I can make a small concession. My offer is ${offer}."
                    if offer < last_offer:
                        offer = last_offer
                        message = f"I can meet you at ${offer}."

                turns.append(NegotiationTurn(round=round_num, agent="seller", offer=offer, message=message))
                if on_turn:
                    on_turn(turns[-1])
                context.append({"agent":"seller","message":message})


                if abs(offer - last_offer) < 0.01:
                    if seller_is_agent:
                        if last_offer >= seller_target:
                            agreed = True
                            final_price = offer
                            reason = "Seller accepted buyer's previous offer."
                            turns[-1].message = f"Deal. I accept ${offer}."
                            break
                        else:
                            counter_offer = max(seller_target, last_offer + 1.0)
                            turns[-1].offer = counter_offer
                            turns[-1].message = "I can't do that, but I can meet you here."
                            offer = counter_offer
                            last_offer = offer
                            context[-1]["message"] = f"I can't do that, but I can meet you here : ${offer}"

                            seller_patience -= 1
                            if seller_is_agent:
                                last_seller_offer = offer
                            agent_turn = "buyer"
                            round_num += 1
                            continue
                    else:
                        agreed = True
                        final_price = offer
                        reason = "Seller accepted buyer's previous offer."
                        turns[-1].message = f"Deal. I accept ${offer}."
                        break

                seller_patience -= 1
                last_offer = offer
                if seller_is_agent:
                    last_seller_offer = offer
                agent_turn = "buyer"
            round_num += 1

        if not agreed:
            reason = "Negotiation ended without agreement (patience exhausted)."


        return NegotiationResult(
            agreed=agreed,
            final_price=final_price,
            turns=turns,
            reason=reason
        )
