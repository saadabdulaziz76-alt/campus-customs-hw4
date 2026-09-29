import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../authContext'

const MIN_PASSWORD = 8

export default function CreateAccount() {
  const { register, user, logout } = useAuth()
  const navigate = useNavigate()
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const mismatch = confirm.length > 0 && password !== confirm

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)

    // Checked here for a fast, friendly response; the server checks again,
    // because anything sent from a browser can be altered.
    if (password !== confirm) {
      setError('Those passwords do not match.')
      return
    }
    if (password.length < MIN_PASSWORD) {
      setError(`Please use at least ${MIN_PASSWORD} characters.`)
      return
    }

    setBusy(true)
    try {
      await register({ firstName, lastName, email, password })
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create the account.')
    } finally {
      setBusy(false)
    }
  }

  if (user) {
    return (
      <div className="page page--form">
        <section className="formCard">
          <p className="hero__eyebrow">Already signed in</p>
          <h1 className="formCard__title">Hello, {user.first_name ?? user.name}</h1>
          <p className="formCard__lede">
            You are signed in as {user.email}. Log out first to create another account.
          </p>
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
        <p className="hero__eyebrow">Join Campus Customs</p>
        <h1 className="formCard__title">Create an account</h1>
        <p className="formCard__lede">
          Keep track of what you have ordered and save your size, so the shop assistant
          can stop asking.
        </p>

        <form className="form" onSubmit={submit}>
          <div className="form__row">
            <label className="field">
              <span className="field__label">First name</span>
              <input
                className="field__input"
                value={firstName}
                onChange={(event) => setFirstName(event.target.value)}
                placeholder="Ada"
                autoComplete="given-name"
                required
              />
            </label>
            <label className="field">
              <span className="field__label">Last name</span>
              <input
                className="field__input"
                value={lastName}
                onChange={(event) => setLastName(event.target.value)}
                placeholder="Lovelace"
                autoComplete="family-name"
                required
              />
            </label>
          </div>

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
              placeholder={`At least ${MIN_PASSWORD} characters`}
              autoComplete="new-password"
              minLength={MIN_PASSWORD}
              required
            />
          </label>

          <label className="field">
            <span className="field__label">Confirm password</span>
            <input
              className={`field__input${mismatch ? ' field__input--bad' : ''}`}
              type="password"
              value={confirm}
              onChange={(event) => setConfirm(event.target.value)}
              placeholder="Type it again"
              autoComplete="new-password"
              required
            />
            {mismatch ? <span className="field__hint">Passwords do not match.</span> : null}
          </label>

          <button
            type="submit"
            className="btn btn--solid btn--lg btn--block"
            disabled={busy || mismatch}
          >
            {busy ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        {error ? <p className="alert alert--form">{error}</p> : null}

        <p className="formCard__foot">
          Already have one? <Link to="/login">Log in</Link>.
        </p>
      </section>
    </div>
  )
}
