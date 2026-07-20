# Homepage — element wiring spec

Companion to `homepage.html`. Every interactive element is annotated inline with an HTML comment at its location in the markup — this doc is the scannable summary of the same information.

## Navigation elements (need real backend routes)

| Element | Example | Route pattern | Backend logic |
|---|---|---|---|
| Type gateway cards (5) | "Vacancies" card | `/vacancy/`, `/admit-card/`, `/result/`, `/answer-key/`, `/notifications/` | Filter: `WHERE notification_type = X`, paginated list. `/notifications/` = no filter, all types. |
| Latest updates feed rows | RRB NTPC row | `/{notification_slug}/` | One page per `notification_id`. Links straight to that specific notification's detail page, not a filtered list. |
| Popular exams chips | "SSC CGL" | `/exam/{exam-slug}/` | Aggregates ALL recruitment cycles for that recurring exam across years — distinct from a single Recruitment Event page. Powers the historical vacancy trend chart. |
| Category cards (16) | "Railways" | `/{category-slug}-jobs/` | Filter: `WHERE recruiting_org.category = X`. |
| State chips | "Maharashtra" | `/{state-slug}-govt-jobs/` | Filter: `WHERE state_or_region IN (X, 'All India')` — central govt posts apply everywhere, must be included alongside the state-specific match. |
| Qualification chips | "10th pass" | `/{qualification-slug}-govt-jobs/` | Filter: `WHERE qualification_level_enum = X`. **Confirm with content team**: should this be exact-match or "floor" match (10th pass filter also shows posts open to 12th pass/graduates, since most notices state a minimum, not a ceiling)? Affects query logic and card counts. |
| Search input | — | `GET /search?q={query}` | Needs `<form action="/search" method="get">` wrapper with `name="q"` on the input — not currently wired to a route, only client-side filtering. |
| "All exams" / "All states" / "View all" links | — | `/exams/`, `/states/`, `/notifications/` | Index pages, not filtered views. |

## Client-side only (no backend route needed)

| Element | Behavior |
|---|---|
| Dark mode toggle | Toggles `data-theme="dark"` on `<html>`, persists to `localStorage('theme')`, defaults to `prefers-color-scheme` on first visit. No server involvement. |
| "Show more categories" button | Toggles `.is-hidden` class on 8 pre-rendered category cards already in the DOM. **Do not** rebuild as a JS-fetched "load more" — the extra cards must stay server-rendered and present at page load so search crawlers index every category link even without executing JS. |
| Search box live filter | Hides/shows visible feed rows as you type — a progressive-enhancement layer on top of the real search route above, not a replacement for it. |

## Data contracts these routes depend on

Every filtered list page (gateway cards, category, state, qualification, exam) is really the same list-view component with a different `WHERE` clause — worth building as one reusable listing template rather than five separate page types. Each pulls from the same base fields defined in the field extraction schema doc (`govt-notification-data-schema.md`), specifically:

- `notification_type` → gateway card filter
- `recruiting_org_name` / category tag → category card filter
- `state_or_region` → state chip filter
- `qualification_level_enum` → qualification chip filter
- `notification_id` / `official_advt_number` → individual detail page identity, exam grouping

## Open questions to resolve before backend build

1. **Qualification filter inclusion rule** (exact vs. floor match) — flagged above, affects both query and expected card counts.
2. **"Popular exams" list is currently hardcoded to 8 entries** — should become data-driven (ranked by actual traffic once analytics exist) rather than a static list maintained by hand.
3. **Gateway card counts and feed counts must share one source of truth** — don't compute "312 vacancies" on the homepage separately from however `/vacancy/` itself counts its results; a mismatch there is a visible, easy-to-notice bug.
