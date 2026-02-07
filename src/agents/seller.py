from .base import BaseAgent

class SellerAgent(BaseAgent):
    def __init__(self, min_price: float):
        super().__init__(role="seller", constraints={"min_price": min_price})
        self.min_price = min_price

    def build_prompt(self, context: str, last_offer: float) -> str:
        return (
            f"You are a seller negotiating the price of a product. "
            f"Your goal is to sell the product for the highest possible price. "
            f"Your absolute minimum acceptable price is ${self.min_price}. "
            f"The negotiation context so far: {context}. "
            f"The last offer from the buyer was ${last_offer}. "
            f"Strategy: Defend your price. Make small concessions only if necessary. "
            f"Do not immediately drop to your minimum price. "
            f"Negotiate like a human trying to maximize profit. "
            f"If the buyer's offer is acceptable and you want to close, you can accept it by repeating that price. "
            f"Reply with a valid JSON object (use double quotes for keys/strings): {{\"offer\": <your_offer>, \"message\": \"<your_short_reasoning>\"}}. "
            f"Never go below your minimum price of ${self.min_price}."
        )
