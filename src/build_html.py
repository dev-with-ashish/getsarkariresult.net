import json
import os
import re
from datetime import datetime

def slugify(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

def update_html_feed(filepath, start_marker, end_marker, new_content):
    if not os.path.exists(filepath):
        return
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        
    pattern = re.compile(rf'({re.escape(start_marker)}).*?({re.escape(end_marker)})', re.DOTALL)
    
    if not pattern.search(content):
        if 'id="latestFeed">' in content:
            content = content.replace('id="latestFeed">', f'id="latestFeed">\n{start_marker}\n{end_marker}')
        elif 'id="vacancyList">' in content:
            content = content.replace('id="vacancyList">', f'id="vacancyList">\n{start_marker}\n{end_marker}')
        
    content = pattern.sub(rf'\1\n{new_content}\n\2', content)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

def conditional_section(html, tag, content, condition):
    """Replace {{#TAG}}...{{/TAG}} blocks based on condition."""
    pattern = re.compile(rf'\{{{{#{tag}\}}}}\s*(.*?)\s*\{{{{\/{tag}\}}}}', re.DOTALL)
    if condition and content:
        html = pattern.sub(r'\1', html)
    else:
        html = pattern.sub('', html)
    return html

def build_json_ld(doc_cat, title, org_name, org_url, notice_ref, vacancies, apply_url, org_slug):
    """Build context-appropriate JSON-LD schema based on document category."""
    base = {
        "@context": "https://schema.org",
        "breadcrumb": {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://getsarkariresult.net/"},
                {"@type": "ListItem", "position": 2, "name": org_name, "item": f"https://getsarkariresult.net/organization-{org_slug}.html"},
                {"@type": "ListItem", "position": 3, "name": title, "item": f"https://getsarkariresult.net/{org_slug}/2026/{notice_ref}"}
            ]
        }
    }

    if doc_cat == "vacancy":
        schema = {
            "@context": "https://schema.org",
            "@type": "JobPosting",
            "title": title,
            "description": f"Official recruitment notification: {title} by {org_name}.",
            "identifier": {"@type": "PropertyValue", "name": org_name, "value": notice_ref},
            "datePosted": datetime.now().strftime("%Y-%m-%d"),
            "employmentType": "FULL_TIME",
            "hiringOrganization": {
                "@type": "GovernmentOrganization",
                "name": org_name,
                "url": org_url
            },
            "jobLocation": {"@type": "Place", "address": {"@type": "PostalAddress", "addressCountry": "IN"}},
            "applicantLocationRequirements": {"@type": "Country", "name": "India"},
            "totalJobOpenings": vacancies,
            "directApply": True,
            "applicationContact": {"@type": "ContactPoint", "url": apply_url}
        }
    else:
        schema = {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": title,
            "description": f"Official {doc_cat.replace('_', ' ')} notification: {title} by {org_name}.",
            "publisher": {"@type": "GovernmentOrganization", "name": org_name, "url": org_url}
        }
    
    return json.dumps(schema, indent=2)

def main():
    try:
        with open("data/jobs.json", "r", encoding="utf-8") as f:
            jobs = json.load(f)
    except FileNotFoundError:
        print("jobs.json not found")
        return
        
    try:
        with open("job-details.html", "r", encoding="utf-8") as f:
            template = f.read()
    except FileNotFoundError:
        print("job-details.html template not found")
        return

    feed_items = []
    vacancy_cards = []
    org_feeds = {}

    active_jobs = [j for j in jobs if j.get("status") == "active"]
    
    for job in active_jobs:
        # Strictly enforce: ONLY display jobs fully analyzed by the AI
        if "documentCategory" not in job:
            continue
            
        title = job.get("title", "Job Update")
        # Clean up junk suffixes that scrapers sometimes add
        for junk in ["Click to know Update", "-- ", "  "]:
            title = title.replace(junk, " ").strip()
        title = re.sub(r'\s{2,}', ' ', title).strip(' -–')

        org_name = job.get("organization", job.get("organizationShort", "ORG"))
        org_short = job.get("organizationShort", org_name)
        org_slug = slugify(org_short)
        org_url = job.get("links", {}).get("officialWebsite") or "#"
        
        year = datetime.now().year
        slug_base = slugify(title)[:50]
        if not slug_base: slug_base = "job"
        slug = f"{slug_base}-{job['id'][:6]}"
        
        silo_dir = f"{org_slug}/{year}"
        os.makedirs(silo_dir, exist_ok=True)
        
        page_path = f"{silo_dir}/{slug}.html"
        is_ai_enriched = "documentCategory" in job
        apply_url = job.get("links", {}).get("officialWebsite") or "#"
        pdf_url = job.get("links", {}).get("notification") or apply_url
        page_url = f"/{page_path}" if is_ai_enriched else (pdf_url or apply_url or "#")
        notice_ref = job.get("id", "")
        
        # ── Determine document category ──────────────────────────────────
        doc_cat = job.get("documentCategory", "").lower()
        if doc_cat not in ["vacancy", "admit_card", "answer_key", "result", "other"]:
            notif_type = str(job.get("notificationType", "")).lower()
            if notif_type in ["recruitment", "vacancy"]:
                doc_cat = "vacancy"
            elif notif_type == "admit_card":
                doc_cat = "admit_card"
            elif notif_type == "answer_key":
                doc_cat = "answer_key"
            elif notif_type == "result":
                doc_cat = "result"
            else:
                doc_cat = "other"

        # ── Category-specific UI labels ──────────────────────────────────
        cat_labels = {
            "vacancy":    ("Active — accepting applications", "is-active", "Apply Online",      "/vacancy.html",      "Vacancies"),
            "admit_card": ("Admit Card Released",             "is-active", "Download Admit Card","/admit-card.html",   "Admit Cards"),
            "answer_key": ("Answer Key Available",            "is-active", "View Answer Key",   "/answer-key.html",   "Answer Keys"),
            "result":     ("Result Declared",                 "is-result", "View Result",       "/result.html",       "Results"),
            "other":      ("Official Notification",           "is-other",  "View Document",     "/notifications.html","Notifications"),
        }
        badge_text, badge_class, btn_label, bc_url, bc_label = cat_labels.get(doc_cat, cat_labels["other"])

        # ── Data fields ──────────────────────────────────────────────────
        vacancies    = job.get("totalVacancies") or "N/A"
        fee          = job.get("applicationFee") or None
        age          = job.get("ageLimit") or None
        qual_list    = job.get("qualifications", [])
        qual         = ", ".join(qual_list) if qual_list else None
        category_sub = job.get("categorySubtitle") or "Official notification"

        # ── Stat row — varies by category ───────────────────────────────
        dates         = job.get("importantDates") or {}
        last_date_val = (dates.get("Last Date to Apply")
                         or dates.get("Last Date")
                         or dates.get("lastDateToApply")
                         or "TBD")
        last_date_short = str(last_date_val)[:25]

        if is_ai_enriched:
            if doc_cat == "vacancy":
                stat_row = f"""
        <div class="stat-cell"><div class="stat-label">Vacancies</div><div class="stat-value">{vacancies}</div></div>
        <div class="stat-cell"><div class="stat-label">Last date</div><div class="stat-value urgent">{last_date_short}</div></div>
        <div class="stat-cell"><div class="stat-label">Age limit</div><div class="stat-value">{age or 'See notification'}</div></div>
        <div class="stat-cell"><div class="stat-label">Qualification</div><div class="stat-value">{(qual or 'Check notification')[:20]}</div></div>"""
            elif doc_cat == "admit_card":
                stat_row = f"""
        <div class="stat-cell"><div class="stat-label">Organization</div><div class="stat-value">{org_short}</div></div>
        <div class="stat-cell"><div class="stat-label">Exam date</div><div class="stat-value">{dates.get('Exam Date') or 'See notification'}</div></div>
        <div class="stat-cell"><div class="stat-label">Available</div><div class="stat-value is-active">{dates.get('Admit Card Available') or 'Now'}</div></div>
        <div class="stat-cell"><div class="stat-label">Hall ticket</div><div class="stat-value">Download</div></div>"""
            elif doc_cat == "answer_key":
                stat_row = f"""
        <div class="stat-cell"><div class="stat-label">Organization</div><div class="stat-value">{org_short}</div></div>
        <div class="stat-cell"><div class="stat-label">Objection deadline</div><div class="stat-value urgent">{dates.get('Last Date to Object') or dates.get('Objection Deadline') or 'See notification'}</div></div>
        <div class="stat-cell"><div class="stat-label">Exam held on</div><div class="stat-value">{dates.get('Exam Date') or 'See notification'}</div></div>
        <div class="stat-cell"><div class="stat-label">Status</div><div class="stat-value">Available</div></div>"""
            elif doc_cat == "result":
                stat_row = f"""
        <div class="stat-cell"><div class="stat-label">Organization</div><div class="stat-value">{org_short}</div></div>
        <div class="stat-cell"><div class="stat-label">Result date</div><div class="stat-value">{dates.get('Result Date') or dates.get('Declaration Date') or last_date_short}</div></div>
        <div class="stat-cell"><div class="stat-label">Candidates</div><div class="stat-value">{vacancies if str(vacancies) != 'N/A' else 'See result'}</div></div>
        <div class="stat-cell"><div class="stat-label">Status</div><div class="stat-value">Declared</div></div>"""
            else:  # other
                stat_row = f"""
        <div class="stat-cell"><div class="stat-label">Organization</div><div class="stat-value">{org_short}</div></div>
        <div class="stat-cell"><div class="stat-label">Published</div><div class="stat-value">{dates.get('Notification Released') or dates.get('notificationDate') or 'See document'}</div></div>
        <div class="stat-cell"><div class="stat-label">Type</div><div class="stat-value">Notice</div></div>
        <div class="stat-cell"><div class="stat-label">Source</div><div class="stat-value">{org_short}</div></div>"""

            # ── Build HTML ───────────────────────────────────────────────────
            html = template

            # Simple replacements
            html = html.replace("{{JOB_TITLE}}",               title)
            html = html.replace("{{NOTICE_REF}}",              str(notice_ref)[:12])
            html = html.replace("{{ORG_NAME}}",                org_name)
            html = html.replace("{{ORG_SLUG}}",                org_slug)
            html = html.replace("{{APPLY_URL}}",               apply_url)
            html = html.replace("{{NOTIFICATION_PDF_URL}}",    pdf_url)
            html = html.replace("{{CATEGORY_SUBTITLE}}",       category_sub)
            html = html.replace("{{STATUS_BADGE_CLASS}}",      badge_class)
            html = html.replace("{{STATUS_BADGE_TEXT}}",       badge_text)
            html = html.replace("{{ACTION_BTN_LABEL}}",        btn_label)
            html = html.replace("{{BREADCRUMB_SECTION_URL}}",  bc_url)
            html = html.replace("{{BREADCRUMB_SECTION_LABEL}}",bc_label)
            html = html.replace("{{STAT_ROW_HTML}}",           stat_row)
            html = html.replace("{{META_DESCRIPTION}}",        f"{badge_text}: {title} — {org_name}. {category_sub}.")
        
            # Important dates table
            dates_html = "".join([f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in dates.items() if v and v != "None"])
            html = conditional_section(html, "IMPORTANT_DATES_SECTION", dates_html, bool(dates_html))
            html = html.replace("{{IMPORTANT_DATES_ROWS}}", dates_html)
        
            # Application fee — only for vacancy/admit_card
            fee_details = job.get("applicationFeeDetails") or {}
            if not fee_details and fee:
                fee_details = {"General": fee}
            fee_html = "".join([f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in fee_details.items()])
            show_fee = doc_cat in ["vacancy", "admit_card"] and bool(fee_html)
            html = conditional_section(html, "FEE_SECTION", fee_html, show_fee)
            html = html.replace("{{APPLICATION_FEE_ROWS}}", fee_html)
            fee_note = job.get("feeNote") or ""
            html = conditional_section(html, "FEE_NOTE_HTML", fee_note, bool(fee_note))
            html = html.replace("{{FEE_NOTE}}", fee_note)

            # Age limit — only for vacancy
            age_details = job.get("ageLimitDetails") or {}
            if not age_details and age:
                age_details = {"Age Limit": age}
            age_html = "".join([f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in age_details.items()])
            show_age = doc_cat == "vacancy" and bool(age_html)
            html = conditional_section(html, "AGE_SECTION", age_html, show_age)
            html = html.replace("{{AGE_LIMIT_ROWS}}", age_html)

            # Vacancy breakdown — only for vacancy
            vac_details = job.get("vacancyBreakdown") or {}
            vac_html = "".join([f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in vac_details.items()])
            show_vac = doc_cat == "vacancy" and bool(vac_html)
            html = conditional_section(html, "VACANCY_SECTION", vac_html, show_vac)
            html = html.replace("{{VACANCY_BREAKDOWN_ROWS}}", vac_html)

            # Eligibility — only for vacancy
            elig_details = job.get("eligibilityDetails") or {}
            elig_summary = job.get("eligibilitySummary") or ""
            if not elig_details and qual:
                elig_details = {"Educational Qualification": qual}
            elig_html = "".join([f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in elig_details.items()])
            show_elig = doc_cat == "vacancy" and (bool(elig_html) or bool(elig_summary))
            html = conditional_section(html, "ELIGIBILITY_SECTION", elig_html or elig_summary, show_elig)
            html = html.replace("{{ELIGIBILITY_SUMMARY}}", elig_summary or "Please refer to official notification.")
            html = html.replace("{{ELIGIBILITY_ROWS}}", elig_html)

            # Selection process — only for vacancy
            steps = job.get("selectionProcess") or []
            if isinstance(steps, str):
                steps = [steps]
            step_html = "".join([f"<li>{s}</li>" for s in steps])
            show_sel = doc_cat == "vacancy" and bool(step_html)
            html = conditional_section(html, "SELECTION_SECTION", step_html, show_sel)
            html = html.replace("{{SELECTION_PROCESS_ROWS}}", step_html)

            # How to apply — only for vacancy (populated by AI extraction if available)
            how_to_apply = job.get("howToApply") or []
            if isinstance(how_to_apply, str):
                how_to_apply = [how_to_apply]
            hta_html = "".join([f"<li>{s}</li>" for s in how_to_apply])
            show_hta = doc_cat == "vacancy" and bool(hta_html)
            html = conditional_section(html, "HOW_TO_APPLY_SECTION", hta_html, show_hta)
            html = html.replace("{{HOW_TO_APPLY_ROWS}}", hta_html)

            # JSON-LD
            json_ld = build_json_ld(doc_cat, title, org_name, org_url, notice_ref, vacancies, apply_url, org_slug)
            html = html.replace("{{JSON_LD_SCHEMA}}", json_ld)

            with open(page_path, "w", encoding="utf-8") as f:
                f.write(html)
            
        # ── Index feed (all active docs) ─────────────────────────────────
        feed_items.append(f'''
        <a class="register-row" href="{page_url}">
          <div class="register-title">{title}</div>
          <div class="register-meta">
            <span class="register-tag">{org_short}</span>
            <span class="register-tag">{bc_label[:-1] if bc_label.endswith('s') else bc_label}</span>
          </div>
        </a>''')
        
        # ── Vacancy feed (only vacancies) ────────────────────────────────
        if doc_cat == "vacancy":
            vacancy_cards.append(f'''
            <a class="vacancy-card" href="{page_url}" data-category="central" data-state="all-india" data-qualification="{slugify(qual or '')}" data-vacancies="{vacancies}" data-days-left="30" data-fee="0">
              <div class="vacancy-main">
                <div class="vacancy-title">{title}</div>
                <div class="vacancy-tags">
                  <span class="vacancy-tag">{org_short}</span>
                </div>
              </div>
              <div class="vacancy-stats">
                <div class="vacancy-stat"><div class="vacancy-stat-num">{vacancies}</div><div class="vacancy-stat-label">Posts</div></div>
                <div class="vacancy-stat"><div class="vacancy-stat-num">{last_date_short}</div><div class="vacancy-stat-label">Last date</div></div>
              </div>
            </a>''')
        
        # ── Org page feed ────────────────────────────────────────────────
        if org_slug not in org_feeds:
            org_feeds[org_slug] = []
        org_feeds[org_slug].append(f'''
        <a class="org-row" href="{page_url}">
          <span class="org-row-title">{title}</span>
          <span class="org-row-meta">{bc_label[:-1] if bc_label.endswith('s') else bc_label}</span>
        </a>''')

    print(f"Generated {len(feed_items)} feed items.")
    # Update global feeds
    update_html_feed("index.html", "<!-- LATEST_FEED_START -->", "<!-- LATEST_FEED_END -->", "".join(feed_items))
    update_html_feed("vacancy.html", "<!-- VACANCY_FEED_START -->", "<!-- VACANCY_FEED_END -->", "".join(vacancy_cards))
    
    # Update org pages
    for org_slug, rows in org_feeds.items():
        org_file = f"organization-{org_slug}.html"
        if os.path.exists(org_file):
            with open(org_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            content = re.sub(r'<div class="empty-section">No active vacancies currently for this organization.</div>', '', content)
            
            marker_start = "<!-- ORG_VACANCY_START -->"
            marker_end = "<!-- ORG_VACANCY_END -->"
            if marker_start not in content:
                pattern = r'(<div class="type-section-title">Vacancies <span class="type-count-badge">.*?</span></div>\s*<a class="type-section-link"[^>]*>View all &rarr;</a>\s*</div>)'
                content = re.sub(pattern, rf'\1\n{marker_start}\n{marker_end}', content)
                
            pattern2 = re.compile(rf'({re.escape(marker_start)}).*?({re.escape(marker_end)})', re.DOTALL)
            content = pattern2.sub(rf'\1\n' + "".join(rows) + rf'\n\2', content)
            content = re.sub(r'(<div class="type-section-title">Vacancies <span class="type-count-badge">)\d+ (active</span></div>)', rf'\g<1>{len(rows)} \g<2>', content)
            
            with open(org_file, "w", encoding="utf-8") as f:
                f.write(content)

    print(f"✅ Generated {len(active_jobs)} HTML pages.")
    print(f"✅ Updated index.html and vacancy.html feeds.")
    print(f"✅ Updated {len(org_feeds)} organization pages.")

if __name__ == "__main__":
    main()
