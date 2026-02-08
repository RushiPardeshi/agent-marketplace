export default function Chat({ turns = [], buyerName, sellerName }) {
  if (!turns.length) {
    return <div className="card">Start a negotiation to see the chat.</div>;
  }

  return (
    <div className="card chat">
      {turns.map((turn, idx) => {
        const role = turn.agent === "buyer" ? "buyer" : turn.agent === "seller" ? "seller" : "system";
        const name = role === "buyer" ? buyerName : role === "seller" ? sellerName : "System";
        return (
          <div className={`bubble ${role}`} key={`${turn.round}-${idx}`}>
            <div className="meta">
              {name} · Round {turn.round} · ${turn.offer}
            </div>
            <div>{turn.message}</div>
          </div>
        );
      })}
    </div>
  );
}
