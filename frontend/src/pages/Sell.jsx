import { useState } from "react";
import { createListing } from "../api/client";
import { useAppContext } from "../state/AppContext.jsx";

export default function Sell() {
  const { sellerName } = useAppContext();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState("");
  const [sellerMinPrice, setSellerMinPrice] = useState("");
  const [category, setCategory] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    setLoading(true);
    setError("");
    try {
      const payload = {
        title,
        description,
        price: Number(price),
        category: category || undefined,
        seller_min_price: sellerMinPrice ? Number(sellerMinPrice) : undefined,
      };
      const data = await createListing(payload);
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
        <h2>List an Item</h2>
        <div className="pill">Signed in as {sellerName}</div>
        <label className="label">Title</label>
        <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} />
        <label className="label" style={{ marginTop: "12px" }}>
          Description
        </label>
        <textarea className="textarea" value={description} onChange={(e) => setDescription(e.target.value)} />
        <div className="grid two" style={{ marginTop: "12px" }}>
          <div>
            <label className="label">Listing price</label>
            <input className="input" value={price} onChange={(e) => setPrice(e.target.value)} />
          </div>
          <div>
            <label className="label">Seller minimum price</label>
            <input className="input" value={sellerMinPrice} onChange={(e) => setSellerMinPrice(e.target.value)} />
          </div>
          <div>
            <label className="label">Category</label>
            <input className="input" value={category} onChange={(e) => setCategory(e.target.value)} />
          </div>
        </div>
        <button className="button" style={{ marginTop: "12px" }} onClick={handleSubmit} disabled={loading}>
          Post listing
        </button>
        {error && <p>{error}</p>}
      </div>

      {result && (
        <div className="card">
          <h3>Listing created</h3>
          <div>{result.title}</div>
          <div>Price: ${result.price}</div>
          <div>ID: {result.id}</div>
        </div>
      )}
    </div>
  );
}
