from openai import OpenAI
from src.config import settings
from src.models.schemas import AIResponse
from typing import List, Tuple, Optional

class BaseAgent:
    def __init__(self, role: str, constraints: dict, agent_id: Optional[str] = None):
        self.role = role
        self.constraints = constraints
        self.agent_id = agent_id or f"{role}_default"
        self.model = settings.OPENAI_MODEL
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def build_prompt(self, context: str, last_offer: float, rounds_left: int, market_context: str = "", product_description: str = "") -> str:
        # To be implemented in subclasses
        raise NotImplementedError
    
    def build_prompt_structured(
        self,
        context: str,
        counterparty_last_offer: float,
        own_offer_history: List[float],
        counterparty_offer_history: List[Tuple[str, float]],
        rounds_left: int,
        market_context: str = "",
        product_description: str = ""
    ) -> str:
        """Build prompt with structured offer history (for multi-agent)"""
        # Default implementation delegates to old method
        # Subclasses should override for better multi-agent support
        return self.build_prompt(context, counterparty_last_offer, rounds_left, market_context, product_description)

    def propose(self, context: str, last_offer: float, rounds_left: int, market_context: str = "", product_description: str = "") -> dict:
        prompt = self.build_prompt(context, last_offer, rounds_left, market_context, product_description)
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
    
    def propose_structured(
        self,
        context: str,
        counterparty_last_offer: float,
        own_offer_history: List[float],
        counterparty_offer_history: List[Tuple[str, float]],
        rounds_left: int,
        market_context: str = "",
        product_description: str = ""
    ) -> dict:
        """Propose with structured offer history (for multi-agent)"""
        prompt = self.build_prompt_structured(
            context,
            counterparty_last_offer,
            own_offer_history,
            counterparty_offer_history,
            rounds_left,
            market_context,
            product_description
        )
        response = self.client.responses.parse(
                model=self.model,
                input=[{"role": "system", "content": prompt}],
                text_format=AIResponse,
                max_output_tokens=1000
            )
        offer_data = response.output_parsed 
        if offer_data is None:
            offer_data = {
                "offer": counterparty_last_offer,
                "message": "Error generating offer"
            }   
            return offer_data
        return offer_data.model_dump()
