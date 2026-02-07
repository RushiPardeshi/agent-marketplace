from src.agents.seller import SellerAgent
from src.agents.buyer import BuyerAgent
from src.models.schemas import NegotiationRequest, NegotiationTurn, NegotiationResult

class NegotiationService:
    def __init__(self, max_rounds: int = 10):
        self.max_rounds = max_rounds

    def negotiate(self, req: NegotiationRequest) -> NegotiationResult:
        seller = SellerAgent(req.seller_min_price)
        buyer = BuyerAgent(req.buyer_max_price)
        turns = []
        context = ""
        round_num = 1
        seller_offer = req.initial_seller_offer or req.product.listing_price
        # buyer_offer is ignored; negotiation starts from seller's listing/initial offer
        last_offer = seller_offer
        agent_turn = "buyer" # Buyer responds to the listing price
        agreed = False
        final_price = None
        reason = None
        while round_num <= self.max_rounds:
            if agent_turn == "buyer":
                offer_data = buyer.propose(context, last_offer)
                offer = offer_data.get("offer", last_offer)
                message = offer_data.get("message", "")
                turns.append(NegotiationTurn(round=round_num, agent="buyer", offer=offer, message=message))
                context += f"\nBuyer offers ${offer}: {message}"
                
                # Check for agreement (convergence)
                if abs(offer - last_offer) < 0.01:
                    agreed = True
                    final_price = offer
                    reason = "Buyer accepted seller's previous offer."
                    break
                    
                last_offer = offer
                agent_turn = "seller"
            else:
                offer_data = seller.propose(context, last_offer)
                offer = offer_data.get("offer", last_offer)
                message = offer_data.get("message", "")
                turns.append(NegotiationTurn(round=round_num, agent="seller", offer=offer, message=message))
                context += f"\nSeller offers ${offer}: {message}"
                
                # Check for agreement (convergence)
                if abs(offer - last_offer) < 0.01:
                    agreed = True
                    final_price = offer
                    reason = "Seller accepted buyer's previous offer."
                    break
                    
                last_offer = offer
                agent_turn = "buyer"
            round_num += 1
        if not agreed:
            reason = "No agreement reached after max rounds."
        return NegotiationResult(
            agreed=agreed,
            final_price=final_price,
            turns=turns,
            reason=reason
        )
