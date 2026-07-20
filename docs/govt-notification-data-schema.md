# Universal Government Notification Data Schema

A single field taxonomy covering every notification type: New Vacancy/Recruitment, Admit Card, Answer Key, Result, Syllabus, Cutoff/Merit List, and General Notification (circulars, exam date changes, corrigendums).

Each field lists which notification types it typically applies to, so your ingestion pipeline can conditionally populate based on detected notification type.

## 1. Core Identity Fields (apply to ALL notification types)

| Field | Type | Applies To | Example | Notes |
|---|---|---|---|---|
| `notification_id` | string | All | `RRB-NTPC-2026-01` | Internal unique ID you generate |
| `official_advt_number` | string | All | `CEN 01/2026` | The org's own advertisement/notice number — critical for dedup |
| `notification_type` | enum | All | `Vacancy` / `Admit Card` / `Answer Key` / `Result` / `Cutoff` / `Syllabus` / `Corrigendum` / `General` | Drives which other fields are relevant |
| `title` | string | All | "RRB NTPC Recruitment 2026" | |
| `recruiting_org_name` | string | All | "Railway Recruitment Board" | Link to Organization entity |
| `recruiting_org_short_code` | string | All | `RRB` | |
| `parent_ministry_department` | string | All | "Ministry of Railways" | Useful for topical clustering |
| `official_source_url` | URL | All | Link to the govt PDF/notice | Always store this — your provenance/trust signal |
| `date_published_by_org` | date | All | Actual date on the notification | Not your ingestion date |
| `date_ingested` | datetime | All | Your system timestamp | For freshness tracking/auditing |
| `last_verified_date` | datetime | All | | Re-verify periodically, flag stale entries |
| `state_or_region` | string/enum | All | "All India" / "Uttar Pradesh" | Central vs state-specific |
| `language_of_notification` | enum | All | `English` / `Hindi` / `Bilingual` | |
| `status` | enum | All | `Upcoming` / `Active` / `Closed` / `Result Declared` / `Cancelled` | Computed field, drives UI badges |

## 2. Vacancy/New Recruitment Notification Fields

| Field | Type | Example | Notes |
|---|---|---|---|
| `post_name(s)` | array | ["Junior Engineer", "Technician"] | One notification often covers multiple posts |
| `total_vacancies` | integer | 6557 | Sum across all posts |
| `vacancy_breakdown_by_post` | table | Post → count | |
| `vacancy_breakdown_by_category` | table | Gen/OBC/SC/ST/EWS counts | Often in a separate annexure |
| `pay_scale_pay_level` | string | "Level-2, ₹19,900–63,200" | Cite 7th CPC level where given |
| `age_limit_min` | integer | 18 | |
| `age_limit_max` | integer | 33 | |
| `age_relaxation_category_wise` | table | OBC +3, SC/ST +5 etc. | |
| `age_reckoned_as_on_date` | date | | Critical — different orgs use different cutoff dates |
| `educational_qualification` | string/structured | "Bachelor's degree in Engineering" | Normalize to a qualification-level enum too |
| `qualification_level_enum` | enum | `10th` / `12th` / `Diploma` / `Graduate` / `PG` / `PhD` | For filtering/faceting on your site |
| `application_mode` | enum | `Online` / `Offline` / `Both` | |
| `application_start_date` | date | | |
| `application_last_date` | date | | **Highest-risk field for accuracy — verify against source every time** |
| `last_date_fee_payment` | date | | Sometimes differs from application last date |
| `correction_window_dates` | date range | | If a "form correction" period is announced |
| `application_fee_general` | number (INR) | 100 | |
| `application_fee_category_wise` | table | SC/ST/PwD often exempted/reduced | |
| `payment_modes_accepted` | array | ["Online", "Challan"] | |
| `selection_process_stages` | array | ["Tier 1 CBT", "Tier 2 CBT", "Document Verification", "Medical"] | Ordered list |
| `exam_pattern_summary` | text | | Keep short; link to full syllabus page |
| `exam_date` | date/range | | Often announced later via separate notice |
| `exam_city_options` | array | | |
| `physical_standards` | structured | Height/chest/endurance | Relevant for Police/Defence posts only |
| `document_checklist` | array | | For DV/interview stage |
| `official_notification_pdf_url` | URL | | |
| `apply_online_url` | URL | | Official application portal link |

## 3. Admit Card Fields

| Field | Type | Example | Notes |
|---|---|---|---|
| `admit_card_release_date` | date | | |
| `exam_date` | date | | Often same notice as admit card |
| `exam_shift_timing` | string | "Shift 1: 9AM–11AM" | |
| `download_url` | URL | | Direct portal link |
| `login_credentials_required` | array | ["Registration No.", "DOB"] | What the user needs to download |
| `exam_center_city` | string | Often shown only post-download | Note as "visible after login" if not public |
| `admit_card_helpline` | string | | Phone/email for issues |

## 4. Answer Key Fields

| Field | Type | Example | Notes |
|---|---|---|---|
| `answer_key_type` | enum | `Provisional` / `Final` | |
| `answer_key_release_date` | date | | |
| `objection_window_start` | date | | |
| `objection_window_end` | date | | |
| `objection_fee_per_question` | number | ₹100 | Some orgs charge per challenged question |
| `download_url` | URL | | |
| `set_wise_keys_available` | boolean | | Multiple question-set versions |

## 5. Result Fields

| Field | Type | Example | Notes |
|---|---|---|---|
| `result_type` | enum | `Prelims` / `Mains` / `Final` / `Interview` | |
| `result_declared_date` | date | | |
| `total_candidates_appeared` | integer | | If published |
| `total_candidates_qualified` | integer | | |
| `cutoff_marks_category_wise` | table | Gen/OBC/SC/ST/EWS/PwD | Highest-traffic single data point on result pages |
| `merit_list_pdf_url` | URL | | |
| `next_stage_details` | text | "Document verification from [date]" | |
| `scorecard_download_url` | URL | | |

## 6. Syllabus / Exam Pattern Fields

| Field | Type | Example | Notes |
|---|---|---|---|
| `exam_stages` | array | | |
| `subject_wise_topics` | structured/table | Subject → topic list | |
| `marking_scheme` | text | "+1 correct, -0.25 wrong" | |
| `negative_marking` | boolean | | |
| `total_marks` | integer | | |
| `exam_duration` | string | "120 minutes" | |
| `medium_of_exam` | array | ["English", "Hindi"] | |
| `official_syllabus_pdf_url` | URL | | |

## 7. Corrigendum / General Notification Fields

| Field | Type | Example | Notes |
|---|---|---|---|
| `related_notification_id` | string | | Links back to the original notice this amends |
| `change_summary` | text | "Last date extended to 20 Aug 2026" | Keep short and specific |
| `field_changed` | enum | `Date` / `Vacancy Count` / `Eligibility` / `Fee` / `Other` | Lets you auto-flag which linked page needs updating |
| `effective_date` | date | | |

## 8. Derived / Computed Fields (you calculate these, not extracted from source)

| Field | Type | Purpose |
|---|---|---|
| `days_remaining_to_apply` | integer | Live countdown widget |
| `is_expiring_soon` | boolean | Triggers UI urgency badge (e.g. <3 days) |
| `similar_posts` | array of IDs | Recommendation engine |
| `historical_vacancy_trend` | chart data | "This org posted X vacancies last year vs Y this year" |
| `normalized_eligibility_summary` | text | One-line plain-language "who can apply" |
| `schema_jobposting_json` | JSON-LD | Auto-generated from the structured fields above |

## Implementation notes

- **Every notification type shares Section 1** — build that as your base table/object, then attach a type-specific extension table (Sections 2–7) via `notification_id` foreign key.
- **`application_last_date` and `cutoff_marks_category_wise` are your two highest-value, highest-risk fields** — highest search volume, and the ones where an extraction error directly harms a real applicant. Consider requiring these two to pass an automated cross-check (e.g. regex-validated against the actual PDF text) before a page auto-publishes.
- **Corrigendum handling is where most competitor sites visibly fail** (I noticed several showing stale dates in the search results above) — building `related_notification_id` linkage from day one lets you auto-propagate date/fee changes to the original listing instead of leaving two contradictory pages live.
