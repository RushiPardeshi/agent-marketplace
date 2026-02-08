from .base import BaseAgent

class BuyerAgent(BaseAgent):
    def __init__(self, max_price: float):
        super().__init__(role="buyer", constraints={"max_price": max_price})
        self.max_price = max_price

    def build_prompt(self, context: str, last_offer: float, rounds_left: int, market_context: str = "", product_description: str = "") -> str:
        urgency_msg = ""
        if rounds_left <= 2:
            urgency_msg = "You are running out of patience. If the seller's offer is within 5% of your target, ACCEPT IT immediately."
        if rounds_left == 1:
            urgency_msg = "FINAL ROUND. If the offer is within your budget, ACCEPT IT. Do not risk losing thlast e item."

        return (
            f"You are an expert buyer negotiating the price of a product. "
            f"Product Description: {product_description} "
            f"CRITICAL RULE: As a buyer, you can only INCREASE or MAINTAIN after your first offer, NEVER DECREASE it. "
            f"Review your previous offers in the context carefully and ensure your new offer is higher or equal to your last offer. "
            f"Your goal is to purchase the product for the lowest possible price. "
            f"Your absolute maximum budget is ${self.max_price}. "
            f"Market Context: {market_context} "
            f"The negotiation context so far: {context}. "
            f"The last offer from the seller was ${last_offer}. "
            f"You have {rounds_left} rounds of negotiation patience left. {urgency_msg} "
            f"Strategy: Start significantly lower than the seller's offer. "
            f"If you have high leverage (many sellers, few buyers), start LOW and be stubborn. "
            f"If you have low leverage (high demand), you may need to offer closer to the listing price early. "
            f"Make small, incremental concessions (e.g., 2-5% change). Do not jump to your maximum budget immediately. "
            f"Try to meet somewhere in the middle between your initial offer and the seller's offer. "
            f"IMPORTANT: Do not accept the first offer unless it is significantly below your max price. Negotiate for a better deal. "
            f"If the seller's offer is high, counter with a lower price instead of accepting immediately. "
            f"Closing Logic: "
            f"1. If rounds_left <= 3 and the seller's offer is <= your current internal target, ACCEPT IT. "
            f"2. If the seller's offer is within 1% of your last offer, ACCEPT IT. "
            f"3. If you have low patience, be willing to increase your offer closer to your max_price to close. "
            f"Reply with a valid JSON object (use double quotes for keys/strings): {{\"offer\": <your_offer>, \"message\": \"<your_short_reasoning>\"}}. "
            f"IMPORTANT: Justify your offer based on market conditions and the product's value. Address the seller's previous arguments if any. "
            f"IMPORTANT: Your offer MUST NEVER exceed ${self.max_price}. "
            f"If your calculated strategic offer is > ${self.max_price}, you MUST offer ${self.max_price} exactly."
            f"If you are about to exceed it, just offer ${self.max_price}. "
            f"IMPORTANT: Never offer a price higher than the seller's last offer. If the seller's offer is acceptable, just repeat it to accept. "
            f"IMPORTANT: Do not explicitly reveal your maximum budget in your messages. Negotiate hard."
        )

    def propose(self, context: str, last_offer: float, rounds_left: int, market_context: str = "", product_description: str = "") -> dict:
        result = super().propose(context, last_offer, rounds_left, market_context, product_description)
        
        # Ensure last_offer is a valid number before comparing
        try:
            valid_last_offer = float(last_offer)
        except (ValueError, TypeError):
            valid_last_offer = 0.0

        # Programmatic safeguard: Rationality check - Don't offer more than the seller is asking
        # if valid_last_offer > 0 and result["offer"] > valid_last_offer:
        #      result["offer"] = valid_last_offer
        #      result["message"] = f"Deal. I accept ${valid_last_offer}."

        # Programmatic safeguard: strict enforcement of ceiling
        # if result["offer"] > self.max_price:
        #     result["offer"] = self.max_price
        #     # Overwrite the message to prevent confusion
        #     result["message"] = f"I cannot go any higher than this."

        # Sanitization: Prevent leaking max price or specific phrases
        msg_lower = result["message"].lower()
        max_price_val = float(self.max_price)
        max_price_str = str(int(max_price_val)) if max_price_val.is_integer() else str(max_price_val)
        
        if (f"${max_price_str}" in result["message"]) or \
           ("only go as high" in msg_lower) or \
           ("maximum" in msg_lower):
            result["message"] = "That's my best offer."

        # Force explicit accept message if repeating offer
        if valid_last_offer > 0 and abs(result["offer"] - valid_last_offer) < 0.01:
             result["message"] = f"Deal. I accept ${valid_last_offer}."

        return result
