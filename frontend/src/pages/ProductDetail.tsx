import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import type { ProductDetail as Detail } from '../api'
import { fetchProduct, imageSrc, money } from '../api'

/**
 * Route wrapper. Keying on productId remounts the inner component when the
 * shopper navigates between products, so its state starts fresh instead of
 * being reset inside an effect.
 */
export default function ProductDetailRoute() {
  const { productId } = useParams<{ productId: string }>()
  return <ProductDetailView key={productId ?? ''} productId={productId ?? ''} />
}

function ProductDetailView({ productId }: { productId: string }) {
  const [product, setProduct] = useState<Detail | null>(null)
  const [selectedSize, setSelectedSize] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!productId) return
    const controller = new AbortController()
    fetchProduct(productId, controller.signal)
      .then((data) => {
        setProduct(data)
        // Preselect the first size that is actually available.
        setSelectedSize(data.sizes.find((s) => s.in_stock)?.size ?? null)
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === 'AbortError') return
        const detail = err instanceof Error ? err.message : 'unknown error'
        setError(
          detail.startsWith('404')
            ? 'That product does not exist.'
            : `Could not load this product (${detail}).`,
        )
      })
      .finally(() => setLoading(false))
    return () => controller.abort()
  }, [productId])

  if (loading) {
    return (
      <div className="page">
        <p className="status">
          <span className="spinner" aria-hidden="true" /> Loading…
        </p>
      </div>
    )
  }

  if (error || !product) {
    return (
      <div className="page">
        <p className="alert">{error ?? 'Product not found.'}</p>
        <Link to="/products" className="btn btn--ghost">
          ← Back to products
        </Link>
      </div>
    )
  }

  const chosen = product.sizes.find((s) => s.size === selectedSize)

  return (
    <div className="page">
      <Link to="/products" className="backLink">
        ← All products
      </Link>

      <div className="detail">
        <div className="detail__media">
          <img className="detail__image" src={imageSrc(product)} alt={product.name} />
        </div>

        <div className="detail__info">
          <p className="detail__type">{product.garment_type}</p>
          <h1 className="detail__name">{product.name}</h1>
          <p className="detail__price">{money(product.price)}</p>

          <p className="detail__desc">{product.description}</p>

          {product.colors.length > 0 ? (
            <div className="detail__block">
              <h2 className="detail__label">Colours</h2>
              <div className="pills">
                {product.colors.map((c) => (
                  <span key={c} className="pill">
                    {c}
                  </span>
                ))}
              </div>
            </div>
          ) : null}

          <div className="detail__block">
            <h2 className="detail__label">
              Size &amp; availability
              <span className="detail__stockNote">{product.total_stock} in stock overall</span>
            </h2>
            <div className="sizes">
              {product.sizes.map((s) => (
                <button
                  key={s.size}
                  className={`size${selectedSize === s.size ? ' size--on' : ''}${
                    s.in_stock ? '' : ' size--out'
                  }`}
                  disabled={!s.in_stock}
                  onClick={() => setSelectedSize(s.size)}
                  title={s.in_stock ? `${s.quantity} available` : 'Out of stock'}
                >
                  {s.size}
                </button>
              ))}
            </div>
            {chosen ? (
              <p className={`stockLine${chosen.quantity <= 3 ? ' stockLine--low' : ''}`}>
                {chosen.quantity > 0
                  ? chosen.quantity <= 3
                    ? `Only ${chosen.quantity} left in ${chosen.size}`
                    : `${chosen.quantity} available in ${chosen.size}`
                  : `Out of stock in ${chosen.size}`}
              </p>
            ) : (
              <p className="stockLine stockLine--low">Every size is currently sold out.</p>
            )}
          </div>

          <button className="btn btn--solid btn--lg btn--block" disabled={!chosen}>
            {chosen ? `Add ${chosen.size} to bag` : 'Unavailable'}
          </button>

          {product.search_tags.length > 0 ? (
            <div className="detail__block">
              <h2 className="detail__label">Tags</h2>
              <div className="pills">
                {product.search_tags.slice(0, 8).map((t) => (
                  <span key={t} className="pill pill--dim">
                    {t}
                  </span>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
