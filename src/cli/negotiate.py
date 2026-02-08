import argparse
import json
import os
from datetime import datetime

from src.agents.human import HumanAgent
from src.models.schemas import NegotiationRequest, Product
from src.services.negotiation import NegotiationService


def _prompt_float(label, default=None):
    while True:
        suffix = f" [{default}]" if default is not None else ""
        raw = input(f"{label}{suffix}: ").strip()
        if not raw and default is not None:
            return float(default)
        try:
            value = float(raw)
        except ValueError:
            print("Please enter a valid number.")
            continue
        if value <= 0:
            print("Value must be greater than 0.")
            continue
        return value


def _prompt_int(label, default=None):
    while True:
        suffix = f" [{default}]" if default is not None else ""
        raw = input(f"{label}{suffix}: ").strip()
        if not raw and default is not None:
            return int(default)
        try:
            value = int(raw)
        except ValueError:
            print("Please enter a valid integer.")
            continue
        if value < 0:
            print("Value must be 0 or greater.")
            continue
        return value


def _ensure_output_path(output_path):
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        return output_path
    out_dir = os.path.join(os.getcwd(), "negotiation_outputs")
    os.makedirs(out_dir, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return os.path.join(out_dir, f"cli_negotiation_{timestamp}.json")


def main():
    parser = argparse.ArgumentParser(description="Human-Agent negotiation CLI")
    parser.add_argument("--role", choices=["buyer", "seller"], required=True, help="Human role in the negotiation")
    parser.add_argument("--product-name", help="Product name")
    parser.add_argument("--product-description", help="Product description")
    parser.add_argument("--listing-price", type=float, help="Listing price")
    parser.add_argument("--seller-min-price", type=float, help="Seller minimum price")
    parser.add_argument("--buyer-max-price", type=float, help="Buyer maximum price")
    parser.add_argument("--active-competitor-sellers", type=int, default=0)
    parser.add_argument("--active-interested-buyers", type=int, default=0)
    parser.add_argument("--initial-seller-offer", type=float)
    parser.add_argument("--initial-buyer-offer", type=float)
    parser.add_argument("--seller-patience", type=int)
    parser.add_argument("--buyer-patience", type=int)
    parser.add_argument("--output-path", help="Path to save the JSON transcript")
    args = parser.parse_args()

    product_name = args.product_name or input("Product name: ").strip()
    product_description = args.product_description or input("Product description (optional): ").strip()
    listing_price = args.listing_price or _prompt_float("Listing price")

    if args.role == "buyer":
        seller_min_price = args.seller_min_price or _prompt_float("Seller minimum price")
        buyer_max_price = args.buyer_max_price or listing_price * 2
    else:
        buyer_max_price = args.buyer_max_price or _prompt_float("Buyer maximum price")
        seller_min_price = args.seller_min_price or listing_price

    initial_seller_offer = args.initial_seller_offer
    if args.role == "seller" and initial_seller_offer is None:
        initial_seller_offer = _prompt_float("Initial seller offer", default=listing_price)

    request = NegotiationRequest(
        product=Product(
            name=product_name,
            description=product_description or None,
            listing_price=listing_price,
        ),
        seller_min_price=seller_min_price,
        buyer_max_price=buyer_max_price,
        active_competitor_sellers=args.active_competitor_sellers,
        active_interested_buyers=args.active_interested_buyers,
        initial_seller_offer=initial_seller_offer,
        initial_buyer_offer=args.initial_buyer_offer,
        seller_patience=args.seller_patience,
        buyer_patience=args.buyer_patience,
    )

    print("\nStarting negotiation...")
    human_agent = HumanAgent(args.role)
    service = NegotiationService()
    def _print_turn(turn):
        if turn.agent != args.role:
            print(f"\n[Agent {turn.agent.title()}]")
            print(f"Offer: ${turn.offer}")
            print(f"Message: {turn.message}")

    result = service.negotiate_with_human(
        request,
        human_role=args.role,
        human_propose=human_agent.propose,
        on_turn=_print_turn,
    )

    print("\nTranscript:")
    for turn in result.turns:
        print(f"Round {turn.round} | {turn.agent}: ${turn.offer} - {turn.message}")
    print(f"\nAgreed: {result.agreed}")
    if result.final_price is not None:
        print(f"Final price: ${result.final_price}")
    if result.reason:
        print(f"Reason: {result.reason}")

    output_path = _ensure_output_path(args.output_path)
    with open(output_path, "w") as f:
        json.dump(result.model_dump(), f, indent=2)
    print(f"\nSaved transcript to {output_path}")


if __name__ == "__main__":
    main()
