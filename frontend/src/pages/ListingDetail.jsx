import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getListing, negotiateListing } from "../api/client";
import Chat from "../components/Chat";
import { useAppContext } from "../state/AppContext.jsx";

function numberOrDefault(value, fallback) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export default function ListingDetail() {
  const { id } = useParams();
  const {
    role,
    buyerName,
    sellerName,
    buyerBudget,
    searchResultsCount,
  } = useAppContext();
  const [listing, setListing] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [mode, setMode] = useState("agent-agent");
  const [sellerMinPrice, setSellerMinPrice] = useState("");
  const [buyerMaxPrice, setBuyerMaxPrice] = useState("");
  const [activeSellers] = useState(1);
  const [activeBuyers] = useState(1);
  const [initialOffer, setInitialOffer] = useState("");
  const [initialMessage, setInitialMessage] = useState("");
  const [result, setResult] = useState(null);
  const [chatTurns, setChatTurns] = useState([]);
  const [offerInput, setOfferInput] = useState("");
  const [messageInput, setMessageInput] = useState("");
  const [counterparty, setCounterparty] = useState("human");
  const [socketStatus, setSocketStatus] = useState("disconnected");
  const [socketError, setSocketError] = useState("");
  const [socketRef] = useState({ current: null });

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const data = await getListing(id);
        setListing(data);
        setSellerMinPrice((data.price * 0.8).toFixed(2));
        setBuyerMaxPrice((data.price * 1.1).toFixed(2));
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [id]);

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/negotiations/${id}`);
    socketRef.current = ws;
    ws.onopen = () => {
      setSocketStatus("connected");
      ws.send(
        JSON.stringify({
          role,
          name: role === "buyer" ? buyerName : sellerName,
          counterparty,
          buyer_max_price: buyerBudget || undefined,
          seller_min_price: sellerMinPrice ? Number(sellerMinPrice) : undefined,
        })
      );
    };
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "state") {
        setChatTurns(data.turns || []);
      } else if (data.type === "turn") {
        setChatTurns((prev) => [...prev, data.turn]);
      } else if (data.type === "error") {
        setSocketError(data.message);
      }
    };
    ws.onclose = () => setSocketStatus("disconnected");
    return () => {
      ws.close();
    };
  }, [id, role, buyerName, sellerName, counterparty, buyerBudget, sellerMinPrice]);

  const handleSendMessage = () => {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      setSocketError("Chat is not connected.");
      return;
    }
    const offer = Number(offerInput);
    if (!Number.isFinite(offer)) {
      setSocketError("Enter a valid offer.");
      return;
    }
    socketRef.current.send(
      JSON.stringify({
        type: "offer",
        offer,
        message: messageInput,
      })
    );
    setOfferInput("");
    setMessageInput("");
  };

  const handleNegotiate = async () => {
    if (!listing) return;
    setLoading(true);
    setError("");
    try {
      const fallbackSellerMin = listing.price * 0.8;
      const fallbackBuyerMax = listing.price * 1.1;
      const payload = {
        buyer_max_price: numberOrDefault(buyerMaxPrice || buyerBudget, fallbackBuyerMax),
        active_competitor_sellers: autoCompetitors,
        active_interested_buyers: autoInterestedBuyers,
      };
      if (role === "seller") {
        payload.seller_min_price = numberOrDefault(sellerMinPrice, fallbackSellerMin);
      }

      if (mode === "human-buyer") {
        payload.initial_buyer_offer = numberOrDefault(initialOffer, payload.buyer_max_price);
        payload.initial_buyer_message = initialMessage || "Initial buyer offer.";
      }

      if (mode === "human-seller") {
        payload.initial_seller_offer = numberOrDefault(initialOffer, listing.price);
        payload.initial_seller_message = initialMessage || "Initial seller offer.";
      }

      const data = await negotiateListing(id, payload);
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading && !listing) {
    return <div>Loading...</div>;
  }

  if (!listing) {
    return <div>{error || "Listing not found."}</div>;
  }

  const autoCompetitors = Math.max(0, (searchResultsCount || 1) - 1);
  const autoInterestedBuyers = role === "seller" ? Math.max(1, searchResultsCount || 1) : 1;

  return (
    <div className="grid">
      <div className="card">
        <h2>{listing.title}</h2>
        <div>{listing.description}</div>
        <div>Price: ${listing.price}</div>
        <div>Category: {listing.category || "N/A"}</div>
      </div>

      <div className="card">
        <h3>Negotiate</h3>
        <div className="pill">Signed in as {role === "buyer" ? buyerName : sellerName}</div>
        <label className="label">Mode</label>
        <select className="select" value={mode} onChange={(e) => setMode(e.target.value)}>
          <option value="agent-agent">Agent ↔ Agent</option>
          <option value="human-buyer">Human Buyer ↔ Seller Agent</option>
          <option value="human-seller">Human Seller ↔ Buyer Agent</option>
        </select>

        <label className="label" style={{ marginTop: "12px" }}>
          Chat counterparty
        </label>
        <select className="select" value={counterparty} onChange={(e) => setCounterparty(e.target.value)}>
          <option value="human">Human</option>
          <option value="agent">Agent</option>
        </select>

        <div className="grid two" style={{ marginTop: "12px" }}>
          {role === "seller" && (
            <div>
              <label className="label">Seller min price</label>
              <input className="input" value={sellerMinPrice} onChange={(e) => setSellerMinPrice(e.target.value)} />
            </div>
          )}
          <div>
            <label className="label">Buyer max price</label>
            <input
              className="input"
              value={buyerMaxPrice}
              onChange={(e) => setBuyerMaxPrice(e.target.value)}
              placeholder={buyerBudget ? String(buyerBudget) : ""}
            />
          </div>
          <div>
            <label className="label">Active competitor sellers</label>
            <input className="input" value={autoCompetitors} disabled />
          </div>
          <div>
            <label className="label">Active interested buyers</label>
            <input className="input" value={autoInterestedBuyers} disabled />
          </div>
        </div>

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

        <button className="button" style={{ marginTop: "12px" }} onClick={handleNegotiate} disabled={loading}>
          Run negotiation
        </button>
        {error && <p>{error}</p>}
      </div>

      <div className="card">
        <h3>Chat</h3>
        <div className="pill">Status: {socketStatus}</div>
        {socketError && <p>{socketError}</p>}
        <Chat turns={chatTurns} buyerName={buyerName} sellerName={sellerName} />
        <div className="grid two" style={{ marginTop: "12px" }}>
          <div>
            <label className="label">Offer</label>
            <input className="input" value={offerInput} onChange={(e) => setOfferInput(e.target.value)} />
          </div>
          <div>
            <label className="label">Message</label>
            <input className="input" value={messageInput} onChange={(e) => setMessageInput(e.target.value)} />
          </div>
        </div>
        <button className="button" style={{ marginTop: "12px" }} onClick={handleSendMessage}>
          Send
        </button>
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
