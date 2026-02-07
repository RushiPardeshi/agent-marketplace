from .base import BaseAgent

class BuyerAgent(BaseAgent):
    def __init__(self, max_price: float):
        super().__init__(role="buyer", constraints={"max_price": max_price})
        self.max_price = max_price

    def build_prompt(self, context: str, last_offer: float, rounds_left: int, market_context: str = "") -> str:
        urgency_msg = ""
        if rounds_left <= 2:
            urgency_msg = "You are running out of patience. You must be more aggressive and push for a deal or make your final offer."
        if rounds_left == 1:
            urgency_msg = "This is your FINAL offer. If the seller does not accept reasonable terms, you will have to walk away. Make your absolute best offer now."

        return (
            f"You are a buyer negotiating the price of a product. "
            f"Your goal is to purchase the product for the lowest possible price. "
            f"Your absolute maximum budget is ${self.max_price}. "
            f"Market Context: {market_context} "
            f"The negotiation context so far: {context}. "
            f"The last offer from the seller was ${last_offer}. "
            f"You have {rounds_left} rounds of negotiation patience left. {urgency_msg} "
            f"Strategy: Start significantly lower than the seller's offer. "
            f"Make small, incremental concessions. Do not jump to your maximum budget immediately. "
            f"Try to meet somewhere in the middle between your initial offer and the seller's offer. "
            f"If the seller's offer is within your budget and seems good, you can accept it by repeating that price. "
            f"Reply with a valid JSON object (use double quotes for keys/strings): {{\"offer\": <your_offer>, \"message\": \"<your_short_reasoning>\"}}. "
            f"Never go above your maximum price of ${self.max_price}."
        )

    def propose(self, context: str, last_offer: float, rounds_left: int, market_context: str = "") -> dict:
        result = super().propose(context, last_offer, rounds_left, market_context)
        # Programmatic safeguard: strict enforcement of ceiling
        if result["offer"] > self.max_price:
            result["offer"] = self.max_price
            if "maximum" not in result["message"].lower():
                 result["message"] += f" I cannot go higher than ${self.max_price}."
        return result
