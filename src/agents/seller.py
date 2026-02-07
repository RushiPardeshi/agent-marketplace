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
            f"Strategy: Start high and concede slowly. "
            f"Your first few offers should be close to the listing price or previous high offers. "
            f"Do not drop to your minimum price immediately. Force the buyer to increase their offer. "
            f"Only drop your price if the buyer is also making concessions. "
            f"If the buyer's offer is acceptable and you want to close, you can accept it by repeating that price. "
            f"Reply with a valid JSON object (use double quotes for keys/strings): {{\"offer\": <your_offer>, \"message\": \"<your_short_reasoning>\"}}. "
            f"Never go below your minimum price of ${self.min_price}."
        )

    def propose(self, context: str, last_offer: float) -> dict:
        result = super().propose(context, last_offer)
        # Programmatic safeguard: strict enforcement of floor
        if result["offer"] < self.min_price:
            result["offer"] = self.min_price
            if "minimum" not in result["message"].lower():
                 result["message"] += f" I cannot go lower than ${self.min_price}."
        return result
