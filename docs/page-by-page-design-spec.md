# Page-by-Page Design Spec — getsarkariresult.net

Eight page types, ordered by traffic value. Each includes: purpose, above-the-fold priority, core modules, and SEO/schema notes.

---

## 1. Recruitment Event Page (flagship — highest traffic + highest value)
`/rrb-ntpc-recruitment-2026/`

**Job:** Convert a search visitor into either an applicant (clicks apply) or a returner (bookmarks/subscribes for updates), inside 3 seconds of landing.

**Above the fold:**
- H1: exact match to search intent — "RRB NTPC Recruitment 2026 — [Post], [Vacancy count] Posts, Apply Online"
- Status badge (Active/Closed/Result Declared) — color-coded, instantly scannable
- The 4 numbers people scan for first, as a tight stat row: **Vacancies · Last Date · Age Limit · Qualification**
- Primary CTA: "Apply Online" (links to official portal) — never fake urgency, real countdown only if `validThrough` is real

**Below fold, in this order (matches actual reading/decision sequence):**
1. Important Dates table (Notification, Start, Last Date, Fee payment, Exam date)
2. Application Fee table (category-wise)
3. Age Limit + relaxation table
4. Vacancy breakdown (post-wise + category-wise)
5. Eligibility (qualification, normalized plain-language summary)
6. Selection Process (numbered stages — this IS a real sequence, numbering justified)
7. How to Apply (step list)
8. Official Links block (Notification PDF, Apply, Official website) — visually distinct, trust-building
9. Related stages nav: Admit Card / Answer Key / Result / Syllabus (auto-links via `related_notification_id`)
10. Similar Posts (recommendation strip)

**SEO/schema:** Full `JobPosting` JSON-LD from your schema doc. This page template is where your entire competitive edge over the four incumbents lives.

---

## 2. Organization Hub Page
`/rrb/` (Railway Recruitment Board)

**Job:** Rank for "[Org] jobs 2026" head terms; aggregate all active + past recruitments under one entity.

**Structure:**
- Org header: name, logo, official site link, one-line mandate description
- Filter bar: Active / Upcoming / Closed / Result Declared
- Card grid of all recruitment events under this org, newest first
- Sidebar: "About [Org]" short entity description (this is where `sameAs`/Wikidata linking pays off)
- Historical vacancy trend chart (your differentiator vs. competitors — nobody else surfaces this)

---

## 3. Admit Card Page
`/rrb-ntpc-admit-card-2026/`

**Job:** Fastest possible path to the download link — this is a low-dwell-time, high-urgency page.

**Above fold:** Download button, release date, direct portal link — nothing else competes for attention here.
**Below fold:** Login credentials needed, exam date/shift, exam center info status, helpline.

---

## 4. Result Page
`/rrb-ntpc-result-2026/`

**Above fold:** Result status, declared date, download/check-result link.
**Below fold:** **Cutoff table (category-wise)** — this is the single highest-dwell-time module on the entire site; give it real visual weight, not a buried table. Next-stage details. Merit list / waiting list links.

---

## 5. State Hub Page
`/uttar-pradesh-govt-jobs/`

**Job:** Capture "[state] sarkari naukri" volume — huge, state-loyal search cluster.
**Structure:** State header, filter by qualification/department, card grid of state-specific recruitments, prominent domicile/local-candidate eligibility notes (a genuine differentiator — competitors bury this).

---

## 6. Qualification Hub Page
`/10th-pass-govt-jobs/`

**Job:** Cross-cutting entity page for "10th pass govt jobs 2026" type searches.
**Structure:** Same card-grid pattern, filtered by `qualification_level_enum` — cheap to build once your data model is right, high-volume standalone traffic.

---

## 7. Homepage
`/`

**Job:** Not actually your main entry point (most traffic lands on #1–2 directly from search) — its job is trust-building and internal navigation for returning visitors.
**Structure:** Live-updating "Latest" feed (Notification/Admit Card/Result tabs), search bar (prominent — many visitors search-within-site), state + category quick links, freshness signal ("Updated X minutes ago" — matches what competitors advertise, don't skip this).

---

## 8. Search / Filter Results Page
`/search?q=...` or `/jobs?state=up&qualification=graduate`

**Job:** Handle the long-tail combinatorial queries your card-grid taxonomy generates.
**Structure:** Faceted filters (state, qualification, category, org, status) as the primary UI element, results as compact list-cards (less visual weight than the hub-page grid, since this is a utility page, optimized for scanning many results fast).

---

## Design language notes (applies across all pages)

- **Status color-coding must be instantly parseable** — this audience scans fast, often on slow mobile connections. Don't rely on subtle color; pair color with a text label always.
- **Mobile-first, non-negotiable.** This audience is overwhelmingly mobile, often on budget devices/slower networks — keep pages light, avoid heavy JS-rendered content that delays the above-fold stat row.
- **Trust signals throughout**: official source links, "last verified" timestamps, and never hiding the official government link behind your own redirect — this audience is understandably wary of unofficial sarkari-job sites (scam risk is real and well-known in this space), and visible trust cues are a genuine differentiator, not just a nicety.
