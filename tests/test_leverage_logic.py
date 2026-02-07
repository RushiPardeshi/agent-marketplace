
def test_leverage_calculation():
    service = NegotiationService()
    
    # Case 1: High Seller Leverage (Many Buyers, Few Sellers)
    # Seller has many buyers (>=3) -> High Leverage -> Low Patience (Aggressive)
    req_high_seller = NegotiationRequest(
        product=Product(name="HotItem", listing_price=100),
        seller_min_price=80,
        buyer_max_price=120,
        active_interested_buyers=5,
        active_competitor_sellers=0
    )
    seller_lev = service._determine_leverage("seller", req_high_seller)
    assert seller_lev == "high"
    assert service._calculate_initial_patience(seller_lev) == 6 # Aggressive
    
    # Case 2: Low Seller Leverage (No Buyers)
    # Seller has 0 buyers -> Low Leverage -> High Patience (Patient)
    req_low_seller = NegotiationRequest(
        product=Product(name="ColdItem", listing_price=100),
        seller_min_price=80,
        buyer_max_price=120,
        active_interested_buyers=0,
        active_competitor_sellers=0
    )
    seller_lev = service._determine_leverage("seller", req_low_seller)
    assert seller_lev == "low"
    assert service._calculate_initial_patience(seller_lev) == 15 # Patient

    # Case 3: High Buyer Leverage (Many Sellers)
    # Buyer has many sellers (>=3) -> High Leverage -> Low Patience (Aggressive)
    req_high_buyer = NegotiationRequest(
        product=Product(name="Commodity", listing_price=100),
        seller_min_price=80,
        buyer_max_price=120,
        active_interested_buyers=0,
        active_competitor_sellers=10
    )
    buyer_lev = service._determine_leverage("buyer", req_high_buyer)
    assert buyer_lev == "high"
    assert service._calculate_initial_patience(buyer_lev) == 6 # Aggressive
