from .base import BaseAgent

class SellerAgent(BaseAgent):
    def __init__(self, min_price: float):
        super().__init__(role="seller", constraints={"min_price": min_price})
        self.min_price = min_price

    def build_prompt(self, context: str, last_offer: float) -> str:
        return (
            f"You are a seller negotiating the price of a product. "
            f"Your minimum acceptable price is ${self.min_price}. "
            f"The negotiation context so far: {context}. "
            f"The last offer was ${last_offer}. "
            f"Reply with a JSON object: {{'offer': <your_offer>, 'message': '<your_reasoning>'}}. "
            f"Never go below your minimum price."
        )
