from openai import OpenAI
from src.config import settings
from src.models.schemas import AIResponse
from openai.types.responses import ResponseInputParam


class BaseAgent:
    def __init__(self, role: str, constraints: dict):
        self.role = role
        self.constraints = constraints
        self.model = settings.OPENAI_MODEL
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def build_prompt(self, last_offer: float, rounds_left: int, market_context: str = "", product_description: str = "") -> str:
        # To be implemented in subclasses
        raise NotImplementedError

    def propose(self, context: list[dict[str,str]], last_offer: float, rounds_left: int, market_context: str = "", product_description: str = "") -> dict:
        conversation_history: ResponseInputParam = []
        for item in context:
            if item["agent"] == self.role:
                conversation_history.append({"role":"assistant","content":item["message"]})
            else:
                conversation_history.append({"role":"user","content":item["message"]})

        prompt = self.build_prompt(last_offer, rounds_left, market_context, product_description)
        response = self.client.responses.parse(
                model=self.model,
                input=[{"role": "system", "content": prompt},*conversation_history],
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
