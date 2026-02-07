from openai import OpenAI
from src.config import settings

class BaseAgent:
    def __init__(self, role: str, constraints: dict):
        self.role = role
        self.constraints = constraints
        self.model = settings.OPENAI_MODEL
        self.temperature = settings.TEMPERATURE
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def build_prompt(self, context: str, last_offer: float) -> str:
        # To be implemented in subclasses
        raise NotImplementedError

    def propose(self, context: str, last_offer: float) -> dict:
        prompt = self.build_prompt(context, last_offer)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": prompt}],
            temperature=self.temperature,
            max_tokens=150,
        )
        content = response.choices[0].message.content.strip()
        # Expecting agent to return a price and a message
        # Example: {"offer": 950, "message": "I can offer at $950 because..."}
        try:
            offer_data = eval(content) if content.startswith("{") else {"offer": float(content)}
        except Exception:
            offer_data = {"offer": last_offer, "message": "Could not parse response."}
        return offer_data
