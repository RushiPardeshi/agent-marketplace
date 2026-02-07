from openai import OpenAI
from src.config import settings
from src.models.schemas import AIResponse

class BaseAgent:
    def __init__(self, role: str, constraints: dict):
        self.role = role
        self.constraints = constraints
        self.model = settings.OPENAI_MODEL
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def build_prompt(self, context: str, last_offer: float, rounds_left: int, market_context: str = "") -> str:
        # To be implemented in subclasses
        raise NotImplementedError

    def propose(self, context: str, last_offer: float, rounds_left: int, market_context: str = "") -> dict:
        prompt = self.build_prompt(context, last_offer, rounds_left, market_context)
        response = self.client.responses.parse(
                model=self.model,
                input=[{"role": "system", "content": prompt}],
                text_format=AIResponse,
                max_output_tokens=1000
            )
        offer_data = response.output_parsed 
        if offer_data is None:
            offer_data = {
                "offer": last_offer,
                "message": "Error generating offer"
            }   
            return offer_data
        return offer_data.model_dump()
