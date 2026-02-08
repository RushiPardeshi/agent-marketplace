import { useState } from "react";
import { negotiate } from "../api/client";
import Chat from "../components/Chat";
import { useAppContext } from "../state/AppContext.jsx";

function numberOrDefault(value, fallback) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export default function Negotiate() {
  const { role, buyerName, sellerName, buyerBudget } = useAppContext();
  const [name, setName] = useState("Laptop");
  const [description, setDescription] = useState("");
  const [listingPrice, setListingPrice] = useState("1200");
  const [sellerMinPrice, setSellerMinPrice] = useState("900");
  const [buyerMaxPrice, setBuyerMaxPrice] = useState("1100");
  const [activeSellers, setActiveSellers] = useState(1);
  const [activeBuyers, setActiveBuyers] = useState(1);
  const [mode, setMode] = useState("agent-agent");
  const [initialOffer, setInitialOffer] = useState("");
  const [initialMessage, setInitialMessage] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    setLoading(true);
    setError("");
    try {
      const listing = numberOrDefault(listingPrice, 1200);
      const payload = {
        product: {
          name,
          description: description || undefined,
          listing_price: listing,
        },
        seller_min_price: numberOrDefault(sellerMinPrice, listing * 0.8),
        buyer_max_price: numberOrDefault(buyerMaxPrice || buyerBudget, listing * 1.1),
        active_competitor_sellers: Number(activeSellers),
        active_interested_buyers: Number(activeBuyers),
      };

      if (mode === "human-buyer") {
        payload.initial_buyer_offer = numberOrDefault(initialOffer, payload.buyer_max_price);
        payload.initial_buyer_message = initialMessage || "Initial buyer offer.";
      }

      if (mode === "human-seller") {
        payload.initial_seller_offer = numberOrDefault(initialOffer, listing);
        payload.initial_seller_message = initialMessage || "Initial seller offer.";
      }

      const data = await negotiate(payload);
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid">
      <div className="card">
        <h2>Manual Negotiation</h2>
        <div className="pill">Signed in as {role === "buyer" ? buyerName : sellerName}</div>
        <div className="grid two">
          <div>
            <label className="label">Product name</label>
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <label className="label">Listing price</label>
            <input className="input" value={listingPrice} onChange={(e) => setListingPrice(e.target.value)} />
          </div>
          <div>
            <label className="label">Seller min price</label>
            <input className="input" value={sellerMinPrice} onChange={(e) => setSellerMinPrice(e.target.value)} />
          </div>
          <div>
            <label className="label">Buyer max price</label>
            <input className="input" value={buyerMaxPrice} onChange={(e) => setBuyerMaxPrice(e.target.value)} />
          </div>
        </div>
        <label className="label" style={{ marginTop: "12px" }}>
          Description
        </label>
        <textarea
          className="textarea"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <div className="grid two" style={{ marginTop: "12px" }}>
          <div>
            <label className="label">Active competitor sellers</label>
            <input className="input" value={activeSellers} onChange={(e) => setActiveSellers(e.target.value)} />
          </div>
          <div>
            <label className="label">Active interested buyers</label>
            <input className="input" value={activeBuyers} onChange={(e) => setActiveBuyers(e.target.value)} />
          </div>
        </div>
        <label className="label" style={{ marginTop: "12px" }}>
          Mode
        </label>
        <select className="select" value={mode} onChange={(e) => setMode(e.target.value)}>
          <option value="agent-agent">Agent ↔ Agent</option>
          <option value="human-buyer">Human Buyer ↔ Seller Agent</option>
          <option value="human-seller">Human Seller ↔ Buyer Agent</option>
        </select>
        {(mode === "human-buyer" || mode === "human-seller") && (
          <div className="grid" style={{ marginTop: "12px" }}>
            <div>
              <label className="label">Initial offer</label>
              <input className="input" value={initialOffer} onChange={(e) => setInitialOffer(e.target.value)} />
            </div>
            <div>
              <label className="label">Initial message</label>
              <textarea
                className="textarea"
                value={initialMessage}
                onChange={(e) => setInitialMessage(e.target.value)}
              />
            </div>
          </div>
        )}
        <button className="button" style={{ marginTop: "12px" }} onClick={handleSubmit} disabled={loading}>
          Run negotiation
        </button>
        {error && <p>{error}</p>}
      </div>

      {result && (
        <div className="grid">
          <div className="card">
            <div>Agreed: {String(result.agreed)}</div>
            <div>Final price: {result.final_price ?? "N/A"}</div>
            <div>Reason: {result.reason || "N/A"}</div>
          </div>
          <Chat turns={result.turns} buyerName={buyerName} sellerName={sellerName} />
        </div>
      )}
    </div>
  );
}
