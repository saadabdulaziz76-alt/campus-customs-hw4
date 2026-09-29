import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../authContext'

export default function Login() {
  const { login, user, logout } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await login(email, password)
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not sign you in.')
    } finally {
      setBusy(false)
    }
  }

  if (user) {
    return (
      <div className="page page--form">
        <section className="formCard">
          <p className="hero__eyebrow">Signed in</p>
          <h1 className="formCard__title">Hello, {user.first_name ?? user.name}</h1>
          <p className="formCard__lede">You are signed in as {user.email}.</p>
          <button className="btn btn--ghost btn--lg btn--block" onClick={logout}>
            Log out
          </button>
        </section>
      </div>
    )
  }

  return (
    <div className="page page--form">
      <section className="formCard">
        <p className="hero__eyebrow">Welcome back</p>
        <h1 className="formCard__title">Log in</h1>
        <p className="formCard__lede">
          Sign in to see your order history and pick up past conversations with the shop
          assistant.
        </p>

        <form className="form" onSubmit={submit}>
          <label className="field">
            <span className="field__label">Email</span>
            <input
              className="field__input"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@yale.edu"
              autoComplete="email"
              required
            />
          </label>

          <label className="field">
            <span className="field__label">Password</span>
            <input
              className="field__input"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
              required
            />
          </label>

          <button type="submit" className="btn btn--solid btn--lg btn--block" disabled={busy}>
            {busy ? 'Signing in…' : 'Log in'}
          </button>
        </form>

        {error ? <p className="alert alert--form">{error}</p> : null}

        <p className="formCard__foot">
          No account yet? <Link to="/create-account">Create one</Link>.
        </p>
      </section>
    </div>
  )
}
