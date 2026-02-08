from .base import BaseAgent
from typing import List, Tuple

class SellerAgent(BaseAgent):
    def __init__(self, min_price: float, agent_id: str = None):
        super().__init__(role="seller", constraints={"min_price": min_price}, agent_id=agent_id)
        self.min_price = min_price

    def build_prompt(self, context: str, last_offer: float, rounds_left: int, market_context: str = "", product_description: str = "") -> str:
        urgency_msg = ""
        if rounds_left <= 2:
            urgency_msg = "You are running out of patience. You MUST become aggressive. If the current offer is within 5% of your target, ACCEPT IT immediately."
        if rounds_left == 1:
            urgency_msg = "FINAL ROUND. If the current offer is profitable at all, ACCEPT IT. Do not risk losing the deal."

        return (
            f"You are an expert seller negotiating the price of a product. "
            f"Product Description: {product_description} "
            f"CRITICAL RULE: As a seller, you can only DECREASE or MAINTAIN your price, NEVER INCREASE it. "
            f"Review your previous offers in the context carefully and ensure your new offer is lower or equal to your last offer. "
            f"Your goal is to sell the product for the highest possible price. "
            f"Your absolute minimum acceptable price is ${self.min_price}. "
            f"Market Context: {market_context} "
            f"The negotiation context so far: {context}. "
            f"The last offer from the buyer was ${last_offer}. "
            f"You have {rounds_left} rounds of negotiation patience left. {urgency_msg} "
            f"Strategy: Start high and concede slowly. "
            f"If you have high leverage (many buyers, few sellers), hold your price firm. "
            f"If you have low leverage (high competition), you may need to drop your price faster to secure the deal. "
            f"Your first few offers should be close to the listing price or previous high offers. "
            f"Do not drop to your minimum price immediately. Force the buyer to increase their offer. "
            f"Only drop your price if the buyer is also making concessions. "
            f"IMPORTANT: Do not accept the first offer unless it is significantly above your min price. Negotiate for a better deal. "
            f"If the buyer's offer is low, counter with a higher price instead of accepting immediately. "
            f"Closing Logic: "
            f"1. If rounds_left <= 3 and the buyer's offer is >= your current internal target, ACCEPT IT. "
            f"2. If the buyer's offer is within 1% of your last offer, ACCEPT IT. "
            f"3. If you have low patience, be willing to drop closer to your min_price to close. "
            f"Reply with a valid JSON object (use double quotes for keys/strings): {{\"offer\": <your_offer>, \"message\": \"<your_short_reasoning>\"}}. "
            f"IMPORTANT: Justify your offer based on the product description and market conditions. Address the buyer's previous arguments if any. "
            f"IMPORTANT: Never go below your minimum price of ${self.min_price}. "
            f"If your calculated strategic offer is < ${self.min_price}, you MUST offer ${self.min_price} exactly. "
            f"IMPORTANT: Never offer a price lower than the buyer's last offer. If the buyer's offer is acceptable, just repeat it to accept. "
            f"IMPORTANT: Do not explicitly reveal your minimum price in your messages. Negotiate hard."
        )
    
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
        """Build prompt with structured history for multi-agent"""
        urgency_msg = ""
        if rounds_left <= 2:
            urgency_msg = "You are running out of patience. You MUST become aggressive. If the current offer is within 5% of your target, ACCEPT IT immediately."
        if rounds_left == 1:
            urgency_msg = "FINAL ROUND. If the current offer is profitable at all, ACCEPT IT. Do not risk losing the deal."
        
        # Format own history
        own_history_str = ""
        if own_offer_history:
            offers_str = ", ".join([f"${o:.2f}" for o in own_offer_history])
            own_history_str = f"Your previous offers: {offers_str}. Your last offer was ${own_offer_history[-1]:.2f}."
        
        # Format counterparty history
        counterparty_str = ""
        if counterparty_offer_history:
            latest = counterparty_offer_history[-1]
            counterparty_str = f"The buyer has offered: {', '.join([f'${o:.2f}' for _, o in counterparty_offer_history])}."

        return (
            f"You are an expert seller (ID: {self.agent_id}) negotiating the price of a product. "
            f"Product Description: {product_description} "
            f"CRITICAL RULE: As a seller, you can only DECREASE or MAINTAIN your price, NEVER INCREASE it. "
            f"{own_history_str} "
            f"Your goal is to sell the product for the highest possible price. "
            f"Your absolute minimum acceptable price is ${self.min_price}. "
            f"Market Context: {market_context} "
            f"{counterparty_str} "
            f"The last offer from the buyer was ${counterparty_last_offer}. "
            f"You have {rounds_left} rounds of negotiation patience left. {urgency_msg} "
            f"Negotiation context: {context}. "
            f"Strategy: Start high and concede slowly. "
            f"If you have high leverage (many buyers, few sellers), hold your price firm. "
            f"If you have low leverage (high competition), you may need to drop your price faster to secure the deal. "
            f"Do not drop to your minimum price immediately. Force the buyer to increase their offer. "
            f"Only drop your price if the buyer is also making concessions. "
            f"IMPORTANT: Do not accept the first offer unless it is significantly above your min price. Negotiate for a better deal. "
            f"If the buyer's offer is low, counter with a higher price instead of accepting immediately. "
            f"Closing Logic: "
            f"1. If rounds_left <= 3 and the buyer's offer is >= your current internal target, ACCEPT IT. "
            f"2. If the buyer's offer is within 1% of your last offer, ACCEPT IT. "
            f"3. If you have low patience, be willing to drop closer to your min_price to close. "
            f"Reply with a valid JSON object (use double quotes for keys/strings): {{\"offer\": <your_offer>, \"message\": \"<your_short_reasoning>\"}}. "
            f"IMPORTANT: Justify your offer based on the product description and market conditions. Address the buyer's previous arguments if any. "
            f"IMPORTANT: Never go below your minimum price of ${self.min_price}. "
            f"If your calculated strategic offer is < ${self.min_price}, you MUST offer ${self.min_price} exactly. "
            f"IMPORTANT: Never offer a price lower than the buyer's last offer. If the buyer's offer is acceptable, just repeat it to accept. "
            f"IMPORTANT: Do not explicitly reveal your minimum price in your messages. Negotiate hard."
        )

    def propose(self, context: str, last_offer: float, rounds_left: int, market_context: str = "", product_description: str = "") -> dict:
        result = super().propose(context, last_offer, rounds_left, market_context, product_description)
        
        # Ensure last_offer is a valid number before comparing
        try:
            valid_last_offer = float(last_offer)
        except (ValueError, TypeError):
            valid_last_offer = 0.0

        # Extract seller's own previous offer from context
        seller_previous_offer = None
        if context:
            # Parse context to find the last seller offer
            lines = context.strip().split('\n')
            for line in reversed(lines):
                if line.startswith('Seller offers $'):
                    try:
                        # Check if this line has a correction suffix "(Corrected to $X)"
                        if "(Corrected to $" in line:
                            # Extract the corrected value
                            corrected_part = line.split("(Corrected to $")[1]
                            seller_previous_offer = float(corrected_part.split(")")[0])
                        else:
                            # Extract the original value
                            seller_previous_offer = float(line.split('$')[1].split(':')[0])
                        break
                    except (ValueError, IndexError):
                        # If the line is not in the expected format, ignore it and continue searching
                        pass

        # Programmatic safeguard: Seller should NEVER increase their offer
        if seller_previous_offer is not None and result["offer"] > seller_previous_offer:
            result["offer"] = seller_previous_offer
            result["message"] = f"I'm holding firm at ${seller_previous_offer}."

        # Programmatic safeguard: Rationality check - Don't offer less than the buyer is willing to pay
        if valid_last_offer > 0 and result["offer"] < valid_last_offer:
             result["offer"] = valid_last_offer
             result["message"] = f"Deal. I accept ${valid_last_offer}."

        # Programmatic safeguard: strict enforcement of floor
        if result["offer"] < self.min_price:
            result["offer"] = self.min_price
            # Overwrite the message to prevent confusion
            result["message"] = f"I cannot go any lower than this."

        # Sanitization: Prevent leaking min price or specific phrases
        msg_lower = result["message"].lower()
        min_price_val = float(self.min_price)
        min_price_str = str(int(min_price_val)) if min_price_val.is_integer() else str(min_price_val)
        
        if (f"${min_price_str}" in result["message"]) or \
           ("minimum" in msg_lower) or \
           ("go below" in msg_lower):
            result["message"] = "That's as low as I can go."
            
        if "go as high" in msg_lower:
            result["message"] = result["message"].replace("go as high", "go as low")

        # Force explicit accept message if repeating offer
        if valid_last_offer > 0 and abs(result["offer"] - valid_last_offer) < 0.01:
             result["message"] = f"Deal. I accept ${valid_last_offer}."

        return result
    
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
        """Propose with structured history - no string parsing needed"""
        result = super().propose_structured(
            context,
            counterparty_last_offer,
            own_offer_history,
            counterparty_offer_history,
            rounds_left,
            market_context,
            product_description
        )
        
        # Ensure counterparty_last_offer is valid
        try:
            valid_last_offer = float(counterparty_last_offer)
        except (ValueError, TypeError):
            valid_last_offer = 0.0
        
        # Use own_offer_history directly instead of parsing context
        seller_previous_offer = own_offer_history[-1] if own_offer_history else None
        
        # Programmatic safeguard: Seller should NEVER increase their offer
        if seller_previous_offer is not None and result["offer"] > seller_previous_offer:
            result["offer"] = seller_previous_offer
            result["message"] = f"I'm holding firm at ${seller_previous_offer}."
        
        # Programmatic safeguard: Rationality check - Don't offer less than the buyer is willing to pay
        if valid_last_offer > 0 and result["offer"] < valid_last_offer:
             result["offer"] = valid_last_offer
             result["message"] = f"Deal. I accept ${valid_last_offer}."
        
        # Programmatic safeguard: strict enforcement of floor
        if result["offer"] < self.min_price:
            result["offer"] = self.min_price
            result["message"] = f"I cannot go any lower than this."
        
        # Sanitization: Prevent leaking min price or specific phrases
        msg_lower = result["message"].lower()
        min_price_val = float(self.min_price)
        min_price_str = str(int(min_price_val)) if min_price_val.is_integer() else str(min_price_val)
        
        if (f"${min_price_str}" in result["message"]) or \
           ("minimum" in msg_lower) or \
           ("go below" in msg_lower):
            result["message"] = "That's as low as I can go."
            
        if "go as high" in msg_lower:
            result["message"] = result["message"].replace("go as high", "go as low")
        
        # Force explicit accept message if repeating offer
        if valid_last_offer > 0 and abs(result["offer"] - valid_last_offer) < 0.01:
             result["message"] = f"Deal. I accept ${valid_last_offer}."
        
        return result
