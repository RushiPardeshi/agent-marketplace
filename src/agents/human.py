class HumanAgent:
    def __init__(self, role: str):
        if role not in {"buyer", "seller"}:
            raise ValueError("role must be 'buyer' or 'seller'")
        self.role = role

    def propose(self, context, last_offer, rounds_left=None, market_context=None, product_description=None):
        header = f"\n[{self.role.title()} Turn]"
        print(header)
        if product_description:
            print(f"Product: {product_description}")
        if market_context:
            print(f"Market: {market_context}")
        if rounds_left is not None:
            print(f"Rounds left: {rounds_left}")
        if last_offer is not None:
            print(f"Last offer: ${last_offer}")

        while True:
            raw_offer = input("Enter offer (number or 'accept'): ").strip()
            if raw_offer.lower() in {"accept", "deal"}:
                if last_offer is None:
                    print("No last offer to accept. Enter a number.")
                    continue
                offer = float(last_offer)
                message = f"Deal. I accept ${offer}."
                return {"offer": offer, "message": message}
            try:
                offer = float(raw_offer)
            except ValueError:
                print("Please enter a valid number or 'accept'.")
                continue
            if offer <= 0:
                print("Offer must be greater than 0.")
                continue
            break

        message = input("Add a short message (optional): ").strip()
        if not message:
            message = "Here is my offer."

        return {"offer": offer, "message": message}
