# Campus Customs — Design

The shop worked before this pass; it just looked like an internal dashboard.
The goal was a storefront a Yale student would trust with $68.

One idea runs through all of it: **the clothes are the only bright thing on the
page.** Everything else is near-black, and the single warm colour is a brass
that appears only on small marks. That contrast is what makes a dark site read
as a boutique rather than a settings screen.

---

## 1 · Type — one voice for the brand, another for the facts

**Bodoni Moda** for anything large: the wordmark, headlines, product names,
prices. It is the typeface of fashion editorial — thin hairlines, dramatic
contrast — and it signals "considered" in a way a UI sans never will.

**Inter** for everything a shopper actually has to read: descriptions, labels,
form fields, chat.

Bodoni is never used below about 17px, where its hairlines break up.

*Why it helps:* the eye now has a hierarchy to follow. A product name in Bodoni
at 17px outranks its description in Inter at 12.5px without needing a heavier
weight or a bigger size. Scanning 102 products stops being work.

## 2 · Colour — near-black, Yale blue, one brass

| Token | Use |
|---|---|
| `--ink` `#08090c` | page, near-black rather than grey |
| Yale blue `#00356b → #17539c` | every action: buttons, active filters, the shopper's own chat bubbles |
| `--brass` `#d4af6a` | the accent — eyebrows, rules, prices in chat, Dan's tag |
| `--good` / `--bad` | stock and errors only |

Blue means *you can click this*. Brass means *this is Campus Customs*. Nothing
else competes.

*Why it helps:* on the old page, headings, links and labels were all variations
of grey-blue, so nothing stood out. Now "Add XS to bag" is the brightest thing
in its column, and it is the thing we want pressed.

## 3 · Product presentation — the fix that mattered most

I measured the catalogue before styling it:

```
102 photos · 92 square · 76 on pure black · 26 on pure white · 0 in between
```

The photos carry their own baked-in backgrounds, in two incompatible flavours.
Any tile colour would clash with one group — my first attempt used a warm bone
tile and produced a visible seam: a cream border around a hard black square.

**So the photo became the tile.** Square frame, image at 100%, `object-fit:
cover`. The square source art lands in a square frame uncropped, and there is no
seam to mismatch. A shared vignette darkens all four edges, which ties the light
and dark photos into one grid and stops the 26 white ones from glaring.

Cards also got: a 4px lift and shadow on hover, a slow 1.06 image zoom, the
garment type in brass small-caps, the price in Bodoni, and a "VIEW" that grows a
brass underline as you approach it.

*Why it helps:* this is the difference between a grid that looks broken and one
that looks art-directed. A shopper who thinks the photos are broken does not
believe the prices either.

## 4 · Motion — direction, never bounce

- Hero rises in four staggered steps on load.
- Sections and cards fade up as they enter view (`IntersectionObserver`, fires
  once, then disconnects — no render-per-scroll).
- A slow marquee of garment types drifts under the hero, masked to fade at both
  ends, and **pauses on hover** so it never fights with reading.
- Chat: messages rise in; the spinner became three drifting dots.

*Why it helps:* movement tells you where you are. The reveal makes a long
catalogue feel like it is arriving rather than already lost below the fold.

## 5 · Chat feel

The assistant writes `**$68**`. That was rendering on screen as literal
asterisks, which made the shop look unfinished. It now renders as real bold **in
brass**, so prices and counts are the first thing you see in a reply. Built as
React nodes, not `innerHTML` — the text comes from a model, so it never gets to
inject markup.

Plus: rounded panel with a blue-wash header, bubbles with a tail, gradient on
the shopper's own messages, and Handsome Dan sitting in the empty state.

## 6 · Handsome Dan

Yale's bulldog, **drawn entirely in CSS** — about 20 `<span>`s, no image file.
Cream body, furrowed brow, underbite, panting tongue, Yale-blue collar with a
brass **Y** tag.

He ambles across the bottom of the window roughly every 36 seconds, tail
wagging, then leaves. He is on a deliberately short leash:

- `pointer-events: none` — he can never intercept a click meant for a product
- `z-index: 30`, below the chat — he passes behind it, never over content
- off entirely under `prefers-reduced-motion`
- off below 760px, where a phone screen has no room to spare
- a footer switch turns him off for good, remembered in `localStorage`

*Why it helps:* it is the one thing on the site nobody else's homework will
have, and it costs the shopper nothing — no payload, no layout shift, no
interference. The restraint is the point: charming for three seconds, then gone.

---

# Verification

Checked in the running app, not just built.

| Check | Result |
|---|---|
| `tsc -b` | clean, exit 0 |
| `oxlint src` | clean, zero warnings |
| Console errors | none (only aborted fetches from `AbortController` on unmount, expected in dev) |
| Bodoni loaded and applied | yes — hero, product names, prices |
| Card seam fix | verified on both a black-background and a white-background product |
| Chat bold | `strongCount: 2` → `["23 hoodies", "$68"]`, `hasLiteralAsterisks: false`, colour `rgb(212,175,106)` |
| Live agent reply | asked "What hoodies do you have?" → 10 cards pushed to the page, results panel rendered |
| Handsome Dan | appears on schedule, `pointer-events: none`, walks behind the chat panel |
| Mobile 375×812 | hero, both CTAs and the marquee fit above the fold |

**Two honest caveats.**

The `prefers-reduced-motion` path is handled in two places — a guard in
`HandsomeDan.tsx` and a global CSS rule that flattens every animation — but I
could not emulate that OS setting in this browser, so it is verified by code
rather than by observation.

The catalogue's light/dark photo split is real and still visible: 26 of 102
cards read brighter than their neighbours. The vignette narrows the gap and the
mix looks deliberate, but only re-shooting or re-masking the source images would
remove it entirely.

Screenshots: `output/screenshots/14-` through `22-design-*.jpg`
