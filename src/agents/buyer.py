from .base import BaseAgent

class BuyerAgent(BaseAgent):
    def __init__(self, max_price: float):
        super().__init__(role="buyer", constraints={"max_price": max_price})
        self.max_price = max_price

    def build_prompt(self, context: str, last_offer: float, rounds_left: int, market_context: str = "") -> str:
        urgency_msg = ""
        if rounds_left <= 2:
            urgency_msg = "You are running out of patience. If the seller's offer is within 5% of your target, ACCEPT IT immediately."
        if rounds_left == 1:
            urgency_msg = "FINAL ROUND. If the offer is within your budget, ACCEPT IT. Do not risk losing the item."

        return (
            f"You are a buyer negotiating the price of a product. "
            f"Your goal is to purchase the product for the lowest possible price. "
            f"Your absolute maximum budget is ${self.max_price}. "
            f"Market Context: {market_context} "
            f"The negotiation context so far: {context}. "
            f"The last offer from the seller was ${last_offer}. "
            f"You have {rounds_left} rounds of negotiation patience left. {urgency_msg} "
            f"Strategy: Start significantly lower than the seller's offer. "
            f"If you have high leverage (many sellers, few buyers), start LOW and be stubborn. "
            f"If you have low leverage (high demand), you may need to offer closer to the listing price early. "
            f"Make small, incremental concessions. Do not jump to your maximum budget immediately. "
            f"Try to meet somewhere in the middle between your initial offer and the seller's offer. "
            f"Closing Logic: "
            f"1. If the seller's offer is <= your current internal target (which may be below max_price), ACCEPT IT by repeating the seller's price. "
            f"2. If the seller's offer is within 1% of your last offer, ACCEPT IT. "
            f"3. If you have low patience, be willing to increase your offer closer to your max_price to close. "
            f"Reply with a valid JSON object (use double quotes for keys/strings): {{\"offer\": <your_offer>, \"message\": \"<your_short_reasoning>\"}}. "
            f"IMPORTANT: Your offer MUST NEVER exceed ${self.max_price}. "
            f"If your calculated strategic offer is > ${self.max_price}, you MUST offer ${self.max_price} exactly."
            f"If you are about to exceed it, just offer ${self.max_price}. "
            f"IMPORTANT: Never offer a price higher than the seller's last offer. If the seller's offer is acceptable, just repeat it to accept."
        )

    def propose(self, context: str, last_offer: float, rounds_left: int, market_context: str = "") -> dict:
        result = super().propose(context, last_offer, rounds_left, market_context)
        
        # Programmatic safeguard: Rationality check - Don't offer more than the seller is asking
        if last_offer > 0 and result["offer"] > last_offer:
             result["offer"] = last_offer
             result["message"] = f"I accept your offer of ${last_offer}. (Adjusted from irrational higher offer)"

        # Programmatic safeguard: strict enforcement of ceiling
        if result["offer"] > self.max_price:
            result["offer"] = self.max_price
            # Overwrite the message to prevent confusion
            result["message"] = f"I cannot go higher than ${self.max_price}. (Adjusted from higher offer)"
        return result
