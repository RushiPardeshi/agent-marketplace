import { useState } from "react";
import { Link } from "react-router-dom";
import { listListings, searchProducts } from "../api/client";
import { useAppContext } from "../state/AppContext.jsx";

export default function Search() {
  const { buyerBudget, setBuyerBudget, setSearchResultsCount } = useAppContext();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [needsBudget, setNeedsBudget] = useState(false);
  const [budgetInput, setBudgetInput] = useState("");

  const handleSearch = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await searchProducts({
        query,
        userBudget: buyerBudget || undefined,
        topK: 10,
        useVector: true,
      });
      setResults(data.results || []);
      setMessage(data.message || "");
      setSearchResultsCount(data.results?.length || 0);
      if (!data.parsed_query?.max_budget) {
        setNeedsBudget(true);
      } else {
        setNeedsBudget(false);
        setBuyerBudget(data.parsed_query.max_budget);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleBrowse = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await listListings(query);
      setResults(
        (data || []).map((listing) => ({
          listing,
          relevance_score: 1,
          reasons: [],
          negotiation_ready: true,
        }))
      );
      setMessage("Showing listings.");
      setSearchResultsCount(data?.length || 0);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleBudgetSubmit = async () => {
    const value = Number(budgetInput);
    if (!Number.isFinite(value) || value <= 0) {
      setError("Enter a valid budget.");
      return;
    }
    setBuyerBudget(value);
    setNeedsBudget(false);
    await handleSearch();
  };

  return (
    <div className="grid">
      <div className="card">
        <h2>Search Marketplace</h2>
        <label className="label">Search query</label>
        <input
          className="input"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Gaming laptop under $1500"
        />
        <div style={{ display: "flex", gap: "12px", marginTop: "12px" }}>
          <button className="button" onClick={handleSearch} disabled={loading}>
            Search with Copilot
          </button>
          <button className="button secondary" onClick={handleBrowse} disabled={loading}>
            Browse Listings
          </button>
        </div>
        {needsBudget && (
          <div style={{ marginTop: "12px" }}>
            <label className="label">What's your maximum budget?</label>
            <input
              className="input"
              value={budgetInput}
              onChange={(e) => setBudgetInput(e.target.value)}
              placeholder="e.g. 1000"
            />
            <button className="button" style={{ marginTop: "8px" }} onClick={handleBudgetSubmit}>
              Update budget
            </button>
          </div>
        )}
        {error && <p>{error}</p>}
        {message && <p>{message}</p>}
      </div>

      <div className="card">
        <h3>Results</h3>
        <div className="grid two">
          {results.map((item) => (
            <div className="card listing-card" key={item.listing.id}>
              <div className="listing-image" />
              <div className="listing-price">${item.listing.price}</div>
              <div className="listing-title">{item.listing.title}</div>
              <div className="listing-desc">{item.listing.description}</div>
              <div style={{ marginTop: "8px" }}>
                <Link to={`/listings/${item.listing.id}`}>Message seller</Link>
              </div>
            </div>
          ))}
          {!results.length && <div>No results yet.</div>}
        </div>
      </div>
    </div>
  );
}
