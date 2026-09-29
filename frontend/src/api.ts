/** Typed client for the Campus Customs API. */

export const API_BASE = 'http://127.0.0.1:8000'

export interface Product {
  product_id: string
  name: string
  garment_type: string
  description: string
  short_description: string
  colors: string[]
  search_tags: string[]
  price: number
  /** Server-relative, e.g. "/images/yale-dad-t-shirt.jpg" */
  image_url: string
  sizes_in_stock: string[]
  sizes_out_of_stock: string[]
  total_stock: number
}

export interface SizeStock {
  size: string
  quantity: number
  in_stock: boolean
}

export interface ProductDetail extends Product {
  sizes: SizeStock[]
  total_stock: number
}

export interface ProductList {
  count: number
  products: Product[]
}

/** The compact product shape the agent attaches to a reply. */
export interface ChatProductCard {
  product_id: string
  name: string
  garment_type: string
  price: number
  image_url: string
  short_description: string
}

export interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
}

/** Where the shopper is, so "do you have this in pink?" has a referent. */
export interface PageContext {
  path: string
  product_id: string | null
}

/** One stored turn, as returned by /api/chat/history. */
export interface StoredMessage {
  role: 'user' | 'assistant'
  content: string
  products: ChatProductCard[]
  created_at: string
}

export interface ChatResponse {
  reply: string
  products: ChatProductCard[]
  /** Heading for the product set when it is shown on the page. */
  result_summary: string
  /** True when the front end should surface these products on the shop page. */
  show_on_page: boolean
  tools_used: string[]
  saved: boolean
  error: string | null
}

/** Product images live on the API, not in the Vite bundle. */
export function imageSrc(product: Pick<Product, 'image_url'>): string {
  return `${API_BASE}${product.image_url}`
}

export function money(value: number): string {
  return `$${value.toFixed(2).replace(/\.00$/, '')}`
}

async function asJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`)
  }
  return (await response.json()) as T
}

export interface ProductQuery {
  q?: string
  garment_type?: string
  /** Only products actually in stock in this size. */
  size?: string
  sort?: 'name' | 'price_asc' | 'price_desc'
}

export const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL'] as const

export async function fetchProducts(
  params: ProductQuery = {},
  signal?: AbortSignal,
): Promise<ProductList> {
  const url = new URL('/api/products', API_BASE)
  for (const [key, value] of Object.entries(params)) {
    if (value) url.searchParams.set(key, value)
  }
  return asJson<ProductList>(await fetch(url, { signal }))
}

export async function fetchProduct(
  productId: string,
  signal?: AbortSignal,
): Promise<ProductDetail> {
  const url = new URL(`/api/products/${encodeURIComponent(productId)}`, API_BASE)
  return asJson<ProductDetail>(await fetch(url, { signal }))
}

export async function fetchGarmentTypes(signal?: AbortSignal): Promise<string[]> {
  const url = new URL('/api/garment-types', API_BASE)
  const data = await asJson<{ garment_types: string[] }>(await fetch(url, { signal }))
  return data.garment_types
}

/**
 * Ask the shop assistant. `authHeader` is optional — the chat works signed out,
 * but a signed-in shopper's conversation gets saved to `chat_messages`.
 */
export async function sendChat(
  message: string,
  history: ChatTurn[] = [],
  authHeader: Record<string, string> = {},
  page: PageContext | null = null,
  signal?: AbortSignal,
): Promise<ChatResponse> {
  const response = await fetch(new URL('/api/chat', API_BASE), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader },
    body: JSON.stringify({ message, history, page }),
    signal,
  })
  return asJson<ChatResponse>(response)
}

/** A signed-in shopper's saved conversation. Requires an auth header. */
export async function fetchChatHistory(
  authHeader: Record<string, string>,
  signal?: AbortSignal,
): Promise<StoredMessage[]> {
  const response = await fetch(new URL('/api/chat/history', API_BASE), {
    headers: authHeader,
    signal,
  })
  const data = await asJson<{ count: number; messages: StoredMessage[] }>(response)
  return data.messages
}
