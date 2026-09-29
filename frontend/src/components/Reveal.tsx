import { useEffect, useRef, type ReactNode } from 'react'

/**
 * Fades a block up as it scrolls into view.
 *
 * Adds a class rather than holding state, so a page full of these does not
 * cause a render per scroll event. Anything already on screen reveals
 * immediately, and the observer disconnects after firing once — the effect is
 * a first impression, not something to replay on every scroll back.
 */
export default function Reveal({
  children,
  delay = 0,
  className = '',
}: {
  children: ReactNode
  /** Stagger, in ms, for items in a row. */
  delay?: number
  className?: string
}) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      el.classList.add('reveal--in')
      return
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return
        el.style.transitionDelay = `${delay}ms`
        el.classList.add('reveal--in')
        observer.disconnect()
      },
      { threshold: 0.12, rootMargin: '0px 0px -40px 0px' },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [delay])

  return (
    <div ref={ref} className={`reveal ${className}`.trim()}>
      {children}
    </div>
  )
}
