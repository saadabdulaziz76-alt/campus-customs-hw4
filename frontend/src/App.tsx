import { BrowserRouter, Route, Routes } from 'react-router-dom'
import './App.css'
import { AuthProvider } from './auth'
import { ChatResultsProvider } from './chatResults'
import NavBar from './components/NavBar'
import ChatPanelKeyed from './components/ChatPanelKeyed'
import HandsomeDan from './components/HandsomeDan'
import Home from './pages/Home'
import Products from './pages/Products'
import ProductDetail from './pages/ProductDetail'
import About from './pages/About'
import Login from './pages/Login'
import CreateAccount from './pages/CreateAccount'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
      <ChatResultsProvider>
      <div className="shell">
        <NavBar />

        <main className="main">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/products" element={<Products />} />
            <Route path="/products/:productId" element={<ProductDetail />} />
            <Route path="/about" element={<About />} />
            <Route path="/login" element={<Login />} />
            <Route path="/create-account" element={<CreateAccount />} />
            <Route
              path="*"
              element={
                <div className="page">
                  <h1 className="pageHead__title">Page not found</h1>
                  <p>That page does not exist. Try the catalogue instead.</p>
                </div>
              }
            />
          </Routes>
        </main>

        <footer className="footer">
          <span>Campus Customs · New Haven, Connecticut</span>
          <span className="footer__dot">·</span>
          <span>Yale apparel since always</span>
          <span className="footer__dot">·</span>
          <HandsomeDan />
        </footer>

        {/* Floating assistant, present on every page */}
        <ChatPanelKeyed />
      </div>
      </ChatResultsProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}
