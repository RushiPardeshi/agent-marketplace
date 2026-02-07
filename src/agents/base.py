import json
import re
import ast
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
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": prompt}],
                temperature=self.temperature,
                max_tokens=150,
            )
            content = response.choices[0].message.content.strip()
            
            # Helper to extract JSON from markdown or raw text
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                try:
                    offer_data = json.loads(json_str)
                except json.JSONDecodeError:
                    # Fallback for Python-style dicts (single quotes)
                    try:
                        offer_data = ast.literal_eval(json_str)
                    except (ValueError, SyntaxError):
                         raise ValueError(f"Could not parse JSON or Dict: {json_str}")
            else:
                # Fallback: try to parse as just a float number
                offer_data = {"offer": float(content.strip()), "message": ""}
                
        except Exception as e:
            # Fallback to last_offer if anything fails (API or parsing)
            # In a real app, we might retry or raise an error
            raw_content = locals().get('content', 'No content')
            offer_data = {
                "offer": last_offer, 
                "message": f"Error generating offer: {str(e)}. Raw: {raw_content}"
            }
            
        return offer_data
