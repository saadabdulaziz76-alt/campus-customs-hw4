import { NavLink } from 'react-router-dom'
import { useAuth } from '../authContext'

const LINKS = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Products' },
  { to: '/about', label: 'About Us' },
]

export default function NavBar() {
  const { user, logout } = useAuth()

  return (
    <header className="nav">
      <div className="nav__inner">
        <NavLink to="/" className="brand">
          <span className="brand__mark">CC</span>
          <span className="brand__text">
            <span className="brand__name">Campus Customs</span>
            <span className="brand__sub">New Haven, Connecticut</span>
          </span>
        </NavLink>

        <nav className="nav__links" aria-label="Main">
          {LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) => `nav__link${isActive ? ' nav__link--active' : ''}`}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>

        <div className="nav__account">
          {user ? (
            <>
              <span className="nav__who" title={user.email}>
                <span className="nav__avatar" aria-hidden="true">
                  {(user.first_name?.[0] ?? user.name[0] ?? '?').toUpperCase()}
                </span>
                {user.first_name ?? user.name}
              </span>
              <button className="btn btn--ghost" onClick={logout}>
                Log Out
              </button>
            </>
          ) : (
            <>
              <NavLink
                to="/login"
                className={({ isActive }) => `btn btn--ghost${isActive ? ' btn--on' : ''}`}
              >
                Log In
              </NavLink>
              <NavLink
                to="/create-account"
                className={({ isActive }) => `btn btn--solid${isActive ? ' btn--on' : ''}`}
              >
                Create Account
              </NavLink>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
