const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }

  return response.json();
}

export function searchProducts({ query, userBudget, topK = 5, useVector = true }) {
  return request("/search", {
    method: "POST",
    body: JSON.stringify({
      query,
      user_budget: userBudget || undefined,
      top_k: topK,
      use_vector: useVector,
    }),
  });
}

export function listListings(query) {
  const q = query ? `?q=${encodeURIComponent(query)}` : "";
  return request(`/listings${q}`);
}

export function getListing(id) {
  return request(`/listings/${id}`);
}

export function negotiate(payload) {
  return request("/negotiate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function negotiateListing(id, payload) {
  return request(`/listings/${id}/negotiate`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createListing(payload) {
  return request("/listings", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
