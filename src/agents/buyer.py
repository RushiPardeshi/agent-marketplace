from .base import BaseAgent

class BuyerAgent(BaseAgent):
    def __init__(self, max_price: float):
        super().__init__(role="buyer", constraints={"max_price": max_price})
        self.max_price = max_price

    def build_prompt(self, context: str, last_offer: float) -> str:
        return (
            f"You are a buyer negotiating the price of a product. "
            f"Your goal is to purchase the product for the lowest possible price. "
            f"Your absolute maximum budget is ${self.max_price}. "
            f"The negotiation context so far: {context}. "
            f"The last offer from the seller was ${last_offer}. "
            f"Strategy: Start significantly lower than the seller's offer but reasonable enough to be taken seriously. "
            f"Make small concessions. Do not immediately jump to your maximum price. "
            f"Negotiate like a human trying to get a deal. "
            f"If the seller's offer is within your budget and seems good, you can accept it by repeating that price. "
            f"Reply with a valid JSON object (use double quotes for keys/strings): {{\"offer\": <your_offer>, \"message\": \"<your_short_reasoning>\"}}. "
            f"Never go above your maximum price of ${self.max_price}."
        )
