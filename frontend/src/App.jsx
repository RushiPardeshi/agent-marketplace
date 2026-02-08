import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import './App.css'
import Search from './pages/Search.jsx'
import ListingDetail from './pages/ListingDetail.jsx'
import Negotiate from './pages/Negotiate.jsx'
import Sell from './pages/Sell.jsx'
import { useAppContext } from './state/AppContext.jsx'

function App() {
  const { role, setRole, buyerName, setBuyerName, sellerName, setSellerName } = useAppContext()

  return (
    <BrowserRouter>
      <div className="app">
        <header className="header">
          <div className="brand">Marketplace</div>
          <nav className="nav">
            <Link to="/">Search</Link>
            <Link to="/sell">Sell</Link>
            <Link to="/negotiate">Negotiate</Link>
          </nav>
          <div className="profile">
            <select className="select" value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="buyer">Buyer</option>
              <option value="seller">Seller</option>
            </select>
            {role === 'buyer' ? (
              <input
                className="input"
                value={buyerName}
                onChange={(e) => setBuyerName(e.target.value)}
                placeholder="Buyer name"
              />
            ) : (
              <input
                className="input"
                value={sellerName}
                onChange={(e) => setSellerName(e.target.value)}
                placeholder="Seller name"
              />
            )}
          </div>
        </header>
        <main className="container">
          <Routes>
            <Route path="/" element={<Search />} />
            <Route path="/listings/:id" element={<ListingDetail />} />
            <Route path="/negotiate" element={<Negotiate />} />
            <Route path="/sell" element={<Sell />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
