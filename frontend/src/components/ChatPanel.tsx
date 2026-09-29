import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useMatch, useNavigate } from 'react-router-dom'
import type { ChatProductCard } from '../api'
import { API_BASE, fetchChatHistory, money, sendChat } from '../api'
import { useAuth } from '../authContext'
import { useChatResults } from '../chatResultsContext'
import { Dan } from './HandsomeDan'

interface Message {
  role: 'user' | 'assistant'
  text: string
  products?: ChatProductCard[]
  /** True when this set was also pushed onto the shop page. */
  onPage?: boolean
  /** True when this came from the database rather than this session. */
  restored?: boolean
  failed?: boolean
}

const SUGGESTIONS = [
  'What hoodies do you have?',
  'Anything under $40?',
  'Do you have a Davenport crewneck?',
]

/** Only the recent turns are replayed; the backend trims further. */
const HISTORY_TURNS = 8

/**
 * The agent writes **bold** for prices and counts. Render those as real bold
 * rather than leaving asterisks on screen.
 *
 * Deliberately builds React nodes instead of setting innerHTML — the text comes
 * from a model, so it never gets to inject markup.
 */
function renderRich(text: string) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**') && part.length > 4 ? (
      <strong key={i}>{part.slice(2, -2)}</strong>
    ) : (
      part
    ),
  )
}

/** Floating shop assistant, wired to the PydanticAI agent behind FastAPI. */
export default function ChatPanel() {
  const { user, authHeader } = useAuth()
  const { setResults } = useChatResults()
  const navigate = useNavigate()
  const location = useLocation()
  // Tells us which product page is open, so "this" has something to point at.
  const productMatch = useMatch('/products/:productId')
  const [historyLoaded, setHistoryLoaded] = useState(false)
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const threadRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, busy, open])

  // A returning signed-in shopper picks up where they left off. Loaded once,
  // the first time they open the panel; guests get a clean slate every visit.
  useEffect(() => {
    if (!open || !user || historyLoaded) return
    const controller = new AbortController()
    fetchChatHistory(authHeader(), controller.signal)
      .then((stored) => {
        if (stored.length === 0) return
        setMessages(
          stored.map((m) => ({
            role: m.role,
            text: m.content,
            products: m.products ?? [],
            restored: true,
          })),
        )
      })
      .catch(() => undefined)
      .finally(() => setHistoryLoaded(true))
    return () => controller.abort()
  }, [open, user, historyLoaded, authHeader])

  async function ask(question: string) {
    const text = question.trim()
    if (!text || busy) return

    const history = messages.slice(-HISTORY_TURNS).map((m) => ({
      role: m.role,
      content: m.text,
    }))

    setMessages((prev) => [...prev, { role: 'user', text }])
    setDraft('')
    setBusy(true)
    try {
      const page = {
        path: location.pathname,
        product_id: productMatch?.params.productId ?? null,
      }
      const data = await sendChat(text, history, authHeader(), page)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: data.reply,
          products: data.products,
          onPage: data.show_on_page && data.products.length > 0,
        },
      ])

      // The agent asked for these to fill the shop page: publish them and take
      // the shopper to the catalogue, where they render as full product cards.
      if (data.show_on_page && data.products.length > 0) {
        setResults(data.products, data.result_summary)
        navigate('/products')
      }
    } catch (error) {
      const detail = error instanceof Error ? error.message : 'unknown error'
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: `Could not reach the shop assistant (${detail}). Is the backend running on port 8000?`,
          failed: true,
        },
      ])
    } finally {
      setBusy(false)
    }
  }

  function onKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      void ask(draft)
    }
  }

  if (!open) {
    return (
      <button className="chatFab" onClick={() => setOpen(true)} aria-label="Open shop assistant">
        <span className="chatFab__dot" aria-hidden="true" />
        Ask us anything
      </button>
    )
  }

  return (
    <section className="chat" aria-label="Shop assistant">
      <header className="chat__head">
        <div>
          <h2 className="chat__title">Shop Assistant</h2>
          <p className="chat__sub">
            {user ? `Signed in as ${user.first_name ?? user.name}` : 'Here to help you find something'}
          </p>
        </div>
        <button className="chat__close" onClick={() => setOpen(false)} aria-label="Close chat">
          ×
        </button>
      </header>

      <div className="chat__thread" ref={threadRef}>
        {messages.length === 0 ? (
          <div className="chat__empty">
            <Dan sitting />
            <p className="chat__emptyText">
              Ask about a garment, a size, a colour, or a price.
            </p>
            <div className="chat__suggestions">
              {SUGGESTIONS.map((s) => (
                <button key={s} className="chip" onClick={() => void ask(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {messages.some((m) => m.restored) ? (
          <p className="chat__restored">Picking up where you left off</p>
        ) : null}

        {messages.map((message, index) => (
          <div
            key={index}
            className={`msg msg--${message.role}${message.failed ? ' msg--failed' : ''}`}
          >
            <div className="msg__body">{renderRich(message.text)}</div>

            {message.onPage ? (
              <button className="msgOnPage" onClick={() => navigate('/products')}>
                <span className="msgOnPage__count">{message.products?.length}</span>
                showing on the page — tap any card to open it
              </button>
            ) : null}

            {message.products && message.products.length > 0 && !message.onPage ? (
              <div className="msgCards">
                {message.products.map((p) => (
                  <Link
                    key={p.product_id}
                    to={`/products/${p.product_id}`}
                    className="msgCard"
                    onClick={() => setOpen(false)}
                  >
                    <img
                      className="msgCard__img"
                      src={`${API_BASE}${p.image_url}`}
                      alt={p.name}
                      loading="lazy"
                    />
                    <span className="msgCard__text">
                      <span className="msgCard__name">{p.name}</span>
                      <span className="msgCard__price">{money(p.price)}</span>
                    </span>
                  </Link>
                ))}
              </div>
            ) : null}
          </div>
        ))}

        {busy ? (
          <div className="msg msg--assistant">
            <div className="msg__body msg__body--thinking">
              <span className="dots" aria-hidden="true">
                <span />
                <span />
                <span />
              </span>
              <span>Looking that up…</span>
            </div>
          </div>
        ) : null}
      </div>

      <form
        className="chat__form"
        onSubmit={(event) => {
          event.preventDefault()
          void ask(draft)
        }}
      >
        <textarea
          className="chat__input"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Ask about a product…"
          rows={2}
          disabled={busy}
        />
        <button type="submit" className="chat__send" disabled={busy || !draft.trim()}>
          Send
        </button>
      </form>
    </section>
  )
}
