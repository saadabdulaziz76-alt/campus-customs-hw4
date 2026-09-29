import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import type { Product } from '../api'
import { SIZES, fetchGarmentTypes, fetchProducts } from '../api'
import ProductCard from '../components/ProductCard'
import { useChatResults } from '../chatResultsContext'

/** 22 raw garment_type values overlap heavily; group them into real categories. */
const CATEGORIES: { label: string; match: string[] }[] = [
  { label: 'All', match: [] },
  { label: 'Hoodies', match: ['hood'] },
  { label: 'Crewnecks', match: ['crewneck', 'crew-neck'] },
  { label: 'T-shirts', match: ['t-shirt', 'tshirt'] },
  { label: 'Quarter-zips', match: ['quarter-zip'] },
  { label: 'Jackets', match: ['jacket'] },
]

export default function Products() {
  const { results, clear } = useChatResults()
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters live in the URL, so a view can be shared, bookmarked, and stepped
  // through with the browser's Back button.
  const [params, setParams] = useSearchParams()
  const query = params.get('q') ?? ''
  const category = params.get('category') ?? 'All'
  const size = params.get('size') ?? ''
  const sort = (params.get('sort') ?? 'name') as 'name' | 'price_asc' | 'price_desc'

  /** Update one filter, dropping it from the URL when it returns to default. */
  function setParam(key: string, value: string, defaultValue = '') {
    const next = new URLSearchParams(params)
    if (!value || value === defaultValue) next.delete(key)
    else next.set(key, value)
    setParams(next, { replace: false })
  }

  useEffect(() => {
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      setLoading(true)
      setError(null)
      fetchProducts(
        { q: query || undefined, size: size || undefined, sort },
        controller.signal,
      )
        .then((data) => setProducts(data.products))
        .catch((err: unknown) => {
          if (err instanceof DOMException && err.name === 'AbortError') return
          const detail = err instanceof Error ? err.message : 'unknown error'
          setError(`Could not load products (${detail}). Is the backend running on port 8000?`)
        })
        .finally(() => setLoading(false))
    }, 200)

    return () => {
      controller.abort()
      window.clearTimeout(timer)
    }
  }, [query, size, sort])

  // Kept so the catalogue's real vocabulary is visible in dev tools even though
  // the UI groups it; also confirms the endpoint works.
  useEffect(() => {
    const controller = new AbortController()
    fetchGarmentTypes(controller.signal).catch(() => undefined)
    return () => controller.abort()
  }, [])

  const shown = useMemo(() => {
    const cat = CATEGORIES.find((c) => c.label === category)
    if (!cat || cat.match.length === 0) return products
    return products.filter((p) => {
      const type = p.garment_type.toLowerCase()
      return cat.match.some((m) => type.includes(m))
    })
  }, [products, category])

  return (
    <div className="page">
      <header className="pageHead">
        <div>
          <p className="hero__eyebrow eyebrow">The catalogue</p>
          <h1 className="pageHead__title">Products</h1>
        </div>
        <p className="pageHead__note">
          {loading ? 'Loading…' : `${shown.length} item${shown.length === 1 ? '' : 's'}`}
        </p>
      </header>
      <hr className="rule" />

      {results ? (
        <section className="chatResults" aria-label="Results from the shop assistant">
          <header className="chatResults__head">
            <div>
              <p className="chatResults__eyebrow">
                <span className="chatResults__dot" aria-hidden="true" />
                From the shop assistant
              </p>
              <h2 className="chatResults__title">{results.summary}</h2>
              <p className="chatResults__count">
                {results.products.length} item{results.products.length === 1 ? '' : 's'} · tap any
                card to open it
              </p>
            </div>
            <button className="btn btn--ghost" onClick={clear}>
              Show all products
            </button>
          </header>

          <div className="grid">
            {results.products.map((p) => (
              <ProductCard
                key={p.product_id}
                product={{
                  product_id: p.product_id,
                  name: p.name,
                  garment_type: p.garment_type,
                  description: p.short_description,
                  short_description: p.short_description,
                  colors: [],
                  search_tags: [],
                  price: p.price,
                  image_url: p.image_url,
                  sizes_in_stock: [],
                  sizes_out_of_stock: [],
                  total_stock: 0,
                }}
              />
            ))}
          </div>
        </section>
      ) : null}

      <div className="controls">
        <div className="search">
          <span className="search__icon" aria-hidden="true">
            ⌕
          </span>
          <input
            className="search__input"
            type="search"
            value={query}
            onChange={(event) => setParam('q', event.target.value)}
            placeholder="Search by name, colour, college, sport…"
            aria-label="Search products"
          />
        </div>

        <label className="select">
          <span className="select__label">Sort</span>
          <select
            className="select__input"
            value={sort}
            onChange={(event) => setParam('sort', event.target.value, 'name')}
          >
            <option value="name">Name</option>
            <option value="price_asc">Price, low to high</option>
            <option value="price_desc">Price, high to low</option>
          </select>
        </label>
      </div>

      <div className="tabs" role="tablist" aria-label="Categories">
        {CATEGORIES.map((c) => (
          <button
            key={c.label}
            role="tab"
            aria-selected={category === c.label}
            className={`tab${category === c.label ? ' tab--on' : ''}`}
            onClick={() => setParam('category', c.label, 'All')}
          >
            {c.label}
          </button>
        ))}
      </div>

      <div className="sizeFilter">
        <span className="sizeFilter__label">In stock in size</span>
        <div className="sizeFilter__options">
          <button
            className={`sizeChip${size === '' ? ' sizeChip--on' : ''}`}
            onClick={() => setParam('size', '')}
          >
            Any
          </button>
          {SIZES.map((s) => (
            <button
              key={s}
              className={`sizeChip${size === s ? ' sizeChip--on' : ''}`}
              onClick={() => setParam('size', size === s ? '' : s)}
            >
              {s}
            </button>
          ))}
        </div>
        {size ? (
          <span className="sizeFilter__note">
            Showing only items you can actually buy in {size}
          </span>
        ) : null}
      </div>

      {error ? <p className="alert">{error}</p> : null}

      {!loading && !error && shown.length === 0 ? (
        <p className="empty">Nothing matches that. Try a broader search.</p>
      ) : null}

      <div className="grid">
        {shown.map((p) => (
          <ProductCard key={p.product_id} product={p} filterSize={size || undefined} />
        ))}
      </div>
    </div>
  )
}
