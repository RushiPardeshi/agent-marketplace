from .base import BaseAgent

class BuyerAgent(BaseAgent):
    def __init__(self, max_price: float):
        super().__init__(role="buyer", constraints={"max_price": max_price})
        self.max_price = max_price

    def build_prompt(self, context: str, last_offer: float) -> str:
        return (
            f"You are a buyer negotiating the price of a product. "
            f"Your maximum acceptable price is ${self.max_price}. "
            f"The negotiation context so far: {context}. "
            f"The last offer was ${last_offer}. "
            f"Reply with a JSON object: {{'offer': <your_offer>, 'message': '<your_reasoning>'}}. "
            f"Never go above your maximum price."
        )
