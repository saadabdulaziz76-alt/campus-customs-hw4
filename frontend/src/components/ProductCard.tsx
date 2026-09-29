import { Link } from 'react-router-dom'
import type { Product } from '../api'
import { imageSrc, money } from '../api'

/** Fewer than this across all sizes counts as running low. */
const LOW_STOCK = 10

interface Props {
  product: Product
  /** When a size filter is active, say whether this item has that size. */
  filterSize?: string
}

export default function ProductCard({ product, filterSize }: Props) {
  const soldOut = product.sizes_out_of_stock?.length ?? 0
  const total = product.total_stock ?? 0
  const lowStock = total > 0 && total < LOW_STOCK

  return (
    <Link to={`/products/${product.product_id}`} className="card">
      <div className="card__imageWrap">
        {lowStock ? (
          <span className="badge badge--low">Low stock</span>
        ) : soldOut > 0 ? (
          <span className="badge badge--partial">
            {soldOut} size{soldOut === 1 ? '' : 's'} sold out
          </span>
        ) : null}

        <img className="card__image" src={imageSrc(product)} alt={product.name} loading="lazy" />
      </div>

      <div className="card__body">
        <p className="card__type">{product.garment_type}</p>
        <h3 className="card__name">{product.name}</h3>
        <p className="card__desc">{product.short_description}</p>

        <div className="card__foot">
          <span className="card__price">{money(product.price)}</span>
          {filterSize && product.sizes_in_stock?.includes(filterSize) ? (
            <span className="card__sizeLeft">{filterSize} in stock</span>
          ) : (
            <span className="card__cta">View →</span>
          )}
        </div>
      </div>
    </Link>
  )
}
