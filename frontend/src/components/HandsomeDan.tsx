import { useEffect, useState } from 'react'

/**
 * Handsome Dan — Yale's bulldog, drawn entirely in CSS (no image files).
 *
 * `Dan` is the dog itself. `HandsomeDan` is the scheduled cameo: every so often
 * he ambles across the very bottom of the window, then leaves. He is decorative
 * and never interactive — `pointer-events: none` on the walking layer means he
 * cannot intercept a click meant for a product.
 *
 * He stays out of the way on purpose: off for anyone who prefers reduced
 * motion, off on small screens, and switchable from the footer, remembered in
 * localStorage.
 */

const STORAGE_KEY = 'cc.handsomeDan'
const FIRST_WAIT_MS = 6_000
const WALK_MS = 17_000
const BETWEEN_MS = 36_000
const MIN_WIDTH = 760

function reducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/** The dog. `sitting` gives the static pose used inside the chat panel. */
export function Dan({ sitting = false }: { sitting?: boolean }) {
  return (
    <div className={`dan${sitting ? ' dan--sit' : ''}`} aria-hidden="true">
      <span className="dan__tail" />
      <span className="dan__leg dan__leg--backFar" />
      <span className="dan__leg dan__leg--frontFar" />
      <span className="dan__torso" />
      <span className="dan__leg dan__leg--back" />
      <span className="dan__leg dan__leg--front" />
      <span className="dan__collar">
        <span className="dan__tag">Y</span>
      </span>
      <span className="dan__head">
        <span className="dan__ear dan__ear--l" />
        <span className="dan__ear dan__ear--r" />
        <span className="dan__brow dan__brow--l" />
        <span className="dan__brow dan__brow--r" />
        <span className="dan__eye dan__eye--l" />
        <span className="dan__eye dan__eye--r" />
        <span className="dan__muzzle">
          <span className="dan__nose" />
          <span className="dan__tooth dan__tooth--l" />
          <span className="dan__tooth dan__tooth--r" />
          <span className="dan__tongue" />
        </span>
      </span>
    </div>
  )
}

/** Footer switch plus the walking cameo. Render once, inside the footer. */
export default function HandsomeDan() {
  const [enabled, setEnabled] = useState(() => localStorage.getItem(STORAGE_KEY) !== 'off')
  const [walking, setWalking] = useState(false)

  useEffect(() => {
    if (!enabled || reducedMotion() || window.innerWidth < MIN_WIDTH) return

    let walkTimer = 0
    let gapTimer = 0

    const stroll = () => {
      setWalking(true)
      walkTimer = window.setTimeout(() => {
        setWalking(false)
        gapTimer = window.setTimeout(stroll, BETWEEN_MS)
      }, WALK_MS)
    }

    const first = window.setTimeout(stroll, FIRST_WAIT_MS)
    return () => {
      clearTimeout(first)
      clearTimeout(walkTimer)
      clearTimeout(gapTimer)
      setWalking(false)
    }
  }, [enabled])

  function toggle() {
    setEnabled((on) => {
      localStorage.setItem(STORAGE_KEY, on ? 'off' : 'on')
      return !on
    })
  }

  return (
    <>
      <button
        type="button"
        className="danToggle"
        onClick={toggle}
        aria-pressed={enabled}
        title={enabled ? 'Let Handsome Dan rest' : 'Let Handsome Dan out'}
      >
        <span className="danToggle__paw" aria-hidden="true" />
        Handsome Dan: {enabled ? 'out' : 'napping'}
      </button>

      {walking ? (
        <div className="danWalk" aria-hidden="true">
          <Dan />
        </div>
      ) : null}
    </>
  )
}
