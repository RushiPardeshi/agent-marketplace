import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getListing } from "../api/client";
import Chat from "../components/Chat";
import { useAppContext } from "../state/AppContext.jsx";

export default function ListingDetail() {
  const { id } = useParams();
  const { role, buyerName, sellerName, buyerBudget } = useAppContext();
  const [listing, setListing] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [delegate, setDelegate] = useState(false);
  const [sellerMinPrice, setSellerMinPrice] = useState("");
  const [buyerMaxPrice, setBuyerMaxPrice] = useState("");
  const [chatTurns, setChatTurns] = useState([]);
  const [offerInput, setOfferInput] = useState("");
  const [messageInput, setMessageInput] = useState("");
  const [socketStatus, setSocketStatus] = useState("disconnected");
  const [socketError, setSocketError] = useState("");
  const [socketRef] = useState({ current: null });
  const [newMessage, setNewMessage] = useState("");
  const [chatRef] = useState({ current: null });

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
          delegate,
          buyer_max_price: Number.isFinite(Number(buyerMaxPrice))
            ? Number(buyerMaxPrice)
            : buyerBudget || undefined,
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
        if (data.turn.agent !== role) {
          const sender = data.turn.agent === "buyer" ? buyerName : sellerName;
          setNewMessage(`New message from ${sender}`);
          if (chatRef.current) {
            chatRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
          }
        }
      } else if (data.type === "error") {
        setSocketError(data.message);
      }
    };
    ws.onclose = () => setSocketStatus("disconnected");
    return () => {
      ws.close();
    };
  }, [id, role, buyerName, sellerName, delegate, buyerBudget, buyerMaxPrice, sellerMinPrice, chatRef]);

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

  if (loading && !listing) {
    return <div>Loading...</div>;
  }

  if (!listing) {
    return <div>{error || "Listing not found."}</div>;
  }

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
        <label className="label" style={{ marginTop: "12px" }}>
          Delegate negotiation to agent
        </label>
        <select className="select" value={delegate ? "yes" : "no"} onChange={(e) => setDelegate(e.target.value === "yes")}>
          <option value="no">No, I will negotiate</option>
          <option value="yes">Yes, let the agent negotiate</option>
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
        </div>
        {error && <p>{error}</p>}
      </div>

      <div className="card">
        <h3 ref={chatRef}>Chat</h3>
        <div className="pill">Status: {socketStatus}</div>
        {newMessage && <div className="pill" style={{ marginTop: "8px" }}>{newMessage}</div>}
        {socketError && <p>{socketError}</p>}
        <Chat turns={chatTurns} buyerName={buyerName} sellerName={sellerName} />
        <div className="grid two" style={{ marginTop: "12px" }}>
          <div>
            <label className="label">Offer</label>
            <input
              className="input"
              value={offerInput}
              onChange={(e) => setOfferInput(e.target.value)}
              disabled={delegate}
            />
          </div>
          <div>
            <label className="label">Message</label>
            <input
              className="input"
              value={messageInput}
              onChange={(e) => setMessageInput(e.target.value)}
              disabled={delegate}
            />
          </div>
        </div>
        <button className="button" style={{ marginTop: "12px" }} onClick={handleSendMessage} disabled={delegate}>
          Send
        </button>
        {delegate && <p>Delegation is enabled. Your agent will negotiate on your behalf.</p>}
      </div>

    </div>
  );
}
