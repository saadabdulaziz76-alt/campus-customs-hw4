import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import type { Product } from '../api'
import { fetchProducts } from '../api'
import ProductCard from '../components/ProductCard'
import Reveal from '../components/Reveal'

/** Drifts across under the hero. Rendered twice so the loop is seamless. */
const MARQUEE = [
  'Crewnecks',
  'Hoodies',
  'Tees',
  'Quarter-zips',
  'Residential colleges',
  'Team kit',
  'New Haven',
]

const PROMISES = [
  {
    num: 'I',
    title: 'Every residential college',
    text: 'Branford to Timothy Dwight, crest and all. If you lived there, we make it.',
  },
  {
    num: 'II',
    title: 'Team kit for the stands',
    text: 'Baseball, crew, diving, hockey, squash — left-chest marks for the sports people actually follow.',
  },
  {
    num: 'III',
    title: 'Something for the family',
    text: 'Yale Dad, Yale Mom, Yale Grandpa. The reliable answer to "bring me something back."',
  },
]

export default function Home() {
  const [featured, setFeatured] = useState<Product[]>([])

  useEffect(() => {
    const controller = new AbortController()
    fetchProducts({ sort: 'name' }, controller.signal)
      .then((data) => {
        // A small, varied selection rather than the first four alphabetically.
        const picks: Product[] = []
        const seen = new Set<string>()
        for (const p of data.products) {
          if (!seen.has(p.garment_type) && picks.length < 4) {
            seen.add(p.garment_type)
            picks.push(p)
          }
        }
        setFeatured(picks)
      })
      .catch(() => setFeatured([]))
    return () => controller.abort()
  }, [])

  return (
    <div className="page">
      <section className="hero">
        <p className="hero__eyebrow eyebrow">Yale apparel · New Haven</p>
        <h1 className="hero__title">
          Wear the place
          <br />
          you <span className="hero__em">belong</span> to.
        </h1>
        <p className="hero__lede">
          Campus Customs makes the sweatshirts, tees and quarter-zips that turn up in
          lecture halls, on the Green, and in the stands at the Bowl. Every piece carries
          a Yale mark — your residential college, your team, or simply the university
          itself — printed on garments built to survive a New England winter and a great
          many laundry cycles.
        </p>
        <div className="hero__actions">
          <Link to="/products" className="btn btn--solid btn--lg">
            Browse the catalogue
          </Link>
          <Link to="/about" className="btn btn--ghost btn--lg">
            About us
          </Link>
          <span className="hero__since">Est. New Haven</span>
        </div>
      </section>

      <div className="marquee" aria-hidden="true">
        <div className="marquee__track">
          {[...MARQUEE, ...MARQUEE].map((word, i) => (
            <span className="marquee__item" key={`${word}-${i}`}>
              {word}
            </span>
          ))}
        </div>
      </div>

      <Reveal>
        <section className="strip">
          {PROMISES.map((p) => (
            <div className="strip__item" key={p.num}>
              <span className="strip__num">{p.num}</span>
              <h3 className="strip__title">{p.title}</h3>
              <p className="strip__text">{p.text}</p>
            </div>
          ))}
        </section>
      </Reveal>

      {featured.length > 0 ? (
        <section className="section">
          <Reveal>
            <div className="section__head">
              <h2 className="section__title">A few things to start with</h2>
              <Link to="/products" className="section__link">
                See everything <span aria-hidden="true">→</span>
              </Link>
            </div>
            <hr className="rule" />
          </Reveal>

          <div className="grid">
            {featured.map((p, i) => (
              <Reveal key={p.product_id} delay={i * 70}>
                <ProductCard product={p} />
              </Reveal>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  )
}
