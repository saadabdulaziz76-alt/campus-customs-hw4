/** Context and hook for chat-driven product results.
 *
 * Kept apart from the provider component so that file exports only a component,
 * which keeps Vite's fast refresh working.
 */

import { createContext, useContext } from 'react'
import type { ChatProductCard } from './api'

export interface ChatResults {
  products: ChatProductCard[]
  summary: string
  /** Bumped on every new result set, so the page reacts even to an identical list. */
  version: number
}

export interface ChatResultsValue {
  results: ChatResults | null
  setResults: (products: ChatProductCard[], summary: string) => void
  clear: () => void
}

export const ChatResultsContext = createContext<ChatResultsValue | null>(null)

export function useChatResults(): ChatResultsValue {
  const context = useContext(ChatResultsContext)
  if (!context) throw new Error('useChatResults must be used inside <ChatResultsProvider>')
  return context
}
