import { createContext, useContext, useMemo, useState } from "react";

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [role, setRole] = useState("buyer");
  const [buyerName, setBuyerName] = useState("You");
  const [sellerName, setSellerName] = useState("Seller");
  const [buyerBudget, setBuyerBudget] = useState(null);
  const [searchResultsCount, setSearchResultsCount] = useState(0);

  const value = useMemo(
    () => ({
      role,
      setRole,
      buyerName,
      setBuyerName,
      sellerName,
      setSellerName,
      buyerBudget,
      setBuyerBudget,
      searchResultsCount,
      setSearchResultsCount,
    }),
    [role, buyerName, sellerName, buyerBudget, searchResultsCount]
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAppContext() {
  const ctx = useContext(AppContext);
  if (!ctx) {
    throw new Error("useAppContext must be used within AppProvider");
  }
  return ctx;
}
