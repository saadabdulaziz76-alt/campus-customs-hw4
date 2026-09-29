/** Holds the products the shop assistant found, so the page can render them.
 *
 * The chat panel writes here when the agent returns a product set; the Products
 * page reads it. Keeping the set in one place is what lets a conversation
 * change what the website is showing.
 */

import { useCallback, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import type { ChatProductCard } from './api'
import { ChatResultsContext } from './chatResultsContext'
import type { ChatResults } from './chatResultsContext'

export function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [results, setStored] = useState<ChatResults | null>(null)

  const setResults = useCallback((products: ChatProductCard[], summary: string) => {
    setStored((prev) => ({
      products,
      summary: summary || 'From your chat',
      version: (prev?.version ?? 0) + 1,
    }))
  }, [])

  const clear = useCallback(() => setStored(null), [])

  const value = useMemo(() => ({ results, setResults, clear }), [results, setResults, clear])

  return <ChatResultsContext.Provider value={value}>{children}</ChatResultsContext.Provider>
}
