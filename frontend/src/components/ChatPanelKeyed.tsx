import ChatPanel from './ChatPanel'
import { useAuth } from '../authContext'

/**
 * Remounts the chat panel whenever the signed-in identity changes.
 *
 * Keying on the user id means signing in or out produces a fresh panel with
 * empty state, so one shopper can never see the tail of another's conversation
 * — and it avoids clearing state inside an effect.
 */
export default function ChatPanelKeyed() {
  const { user } = useAuth()
  return <ChatPanel key={user?.id ?? 'guest'} />
}
