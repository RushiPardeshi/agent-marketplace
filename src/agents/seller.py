from .base import BaseAgent

class SellerAgent(BaseAgent):
    def __init__(self, min_price: float):
        super().__init__(role="seller", constraints={"min_price": min_price})
        self.min_price = min_price

    def build_prompt(self, context: str, last_offer: float, rounds_left: int, market_context: str = "") -> str:
        urgency_msg = ""
        if rounds_left <= 2:
            urgency_msg = "You are running out of patience. You MUST become aggressive. If the current offer is within 5% of your target, ACCEPT IT immediately."
        if rounds_left == 1:
            urgency_msg = "FINAL ROUND. If the current offer is profitable at all, ACCEPT IT. Do not risk losing the deal."

        return (
            f"You are a seller negotiating the price of a product. "
            f"Your goal is to sell the product for the highest possible price. "
            f"Your absolute minimum acceptable price is ${self.min_price}. "
            f"Market Context: {market_context} "
            f"The negotiation context so far: {context}. "
            f"The last offer from the buyer was ${last_offer}. "
            f"You have {rounds_left} rounds of negotiation patience left. {urgency_msg} "
            f"Strategy: Start high and concede slowly. "
            f"If you have high leverage (many buyers, few sellers), hold your price firm. "
            f"If you have low leverage (high competition), you may need to drop your price faster to secure the deal. "
            f"Your first few offers should be close to the listing price or previous high offers. "
            f"Do not drop to your minimum price immediately. Force the buyer to increase their offer. "
            f"Only drop your price if the buyer is also making concessions. "
            f"Closing Logic: "
            f"1. If the buyer's offer is >= your current internal target (which may be above min_price), ACCEPT IT by repeating the buyer's price. "
            f"2. If the buyer's offer is within 1% of your last offer, ACCEPT IT. "
            f"3. If you have low patience, be willing to drop closer to your min_price to close. "
            f"Reply with a valid JSON object (use double quotes for keys/strings): {{\"offer\": <your_offer>, \"message\": \"<your_short_reasoning>\"}}. "
            f"IMPORTANT: Never go below your minimum price of ${self.min_price}. "
            f"If your calculated strategic offer is < ${self.min_price}, you MUST offer ${self.min_price} exactly. "
            f"IMPORTANT: Never offer a price lower than the buyer's last offer. If the buyer's offer is acceptable, just repeat it to accept."
        )

    def propose(self, context: str, last_offer: float, rounds_left: int, market_context: str = "") -> dict:
        result = super().propose(context, last_offer, rounds_left, market_context)
        
        # Ensure last_offer is a valid number before comparing
        try:
            valid_last_offer = float(last_offer)
        except (ValueError, TypeError):
            valid_last_offer = 0.0

        # Programmatic safeguard: Rationality check - Don't offer less than the buyer is willing to pay
        if valid_last_offer > 0 and result["offer"] < valid_last_offer:
             result["offer"] = valid_last_offer
             result["message"] = f"I accept your offer of ${valid_last_offer}. (Adjusted from irrational lower offer)"

        # Programmatic safeguard: strict enforcement of floor
        if result["offer"] < self.min_price:
            result["offer"] = self.min_price
            # Overwrite the message to prevent confusion
            result["message"] = f"I cannot go lower than ${self.min_price}. (Adjusted from lower offer)"
        return result
