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
        seller_offer = req.initial_seller_offer or req.seller_min_price
        buyer_offer = req.initial_buyer_offer or req.buyer_max_price
        last_offer = seller_offer
        agent_turn = "buyer"
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
                if offer >= seller.min_price:
                    agreed = True
                    final_price = offer
                    reason = "Buyer accepted seller's minimum price."
                    break
                last_offer = offer
                agent_turn = "seller"
            else:
                offer_data = seller.propose(context, last_offer)
                offer = offer_data.get("offer", last_offer)
                message = offer_data.get("message", "")
                turns.append(NegotiationTurn(round=round_num, agent="seller", offer=offer, message=message))
                context += f"\nSeller offers ${offer}: {message}"
                if offer <= buyer.max_price:
                    agreed = True
                    final_price = offer
                    reason = "Seller accepted buyer's maximum price."
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
