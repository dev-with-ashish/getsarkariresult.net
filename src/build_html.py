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
    
    # If markers don't exist, try to inject them (one-time setup for our empty templates)
    if not pattern.search(content):
        if "id=\"latestFeed\">" in content:
            content = content.replace('id="latestFeed">', f'id="latestFeed">\n{start_marker}\n{end_marker}')
        elif "id=\"vacancyList\">" in content:
            content = content.replace('id="vacancyList">', f'id="vacancyList">\n{start_marker}\n{end_marker}')
        
    content = pattern.sub(rf'\1\n{new_content}\n\2', content)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

def main():
    try:
        with open("data/jobs.json", "r", encoding="utf-8") as f:
            jobs = json.load(f)
    except FileNotFoundError:
        print("jobs.json not found")
        return
        
    try:
        with open("job-details.html", "r", encoding="utf-8") as f:
            template_vacancy = f.read()
        with open("template-generic.html", "r", encoding="utf-8") as f:
            template_generic = f.read()
    except FileNotFoundError:
        print("Templates not found")
        return

    feed_items = []
    vacancy_cards = []
    
    # Group jobs by organization for org page feeds
    org_feeds = {}

    active_jobs = [j for j in jobs if j.get("status") == "active"]
    
    for job in active_jobs:
        title = job.get("title", "Job Update")
        org_short = job.get("organizationShort", "ORG")
        slug_base = slugify(title)[:50]
        if not slug_base: slug_base = "job"
        slug = f"{slug_base}-{job['id'][:6]}"
        
        org_slug = slugify(org_short)
        year = datetime.now().year
        
        silo_dir = f"{org_slug}/{year}"
        os.makedirs(silo_dir, exist_ok=True)
        
        page_path = f"{silo_dir}/{slug}.html"
        page_url = f"/{page_path}"
        
        vacancies = job.get("totalVacancies") or "Various"
        fee = job.get("applicationFee") or "Check Notification"
        age = job.get("ageLimit") or "Check Notification"
        qual = ", ".join(job.get("qualifications", [])) if job.get("qualifications") else "Check Notification"
        apply_url = job.get("links", {}).get("officialWebsite") or "#"
        notice_ref = job.get("id")
        
        # Determine Category and Template
        doc_cat = job.get("documentCategory", "other").lower()
        if doc_cat not in ["vacancy", "admit_card", "answer_key", "result"]:
            notif_type = str(job.get("notificationType", "")).lower()
            if notif_type in ["recruitment", "vacancy", "admit_card", "answer_key", "result"]:
                doc_cat = "vacancy"
            else:
                doc_cat = "other"
                
        is_vacancy = doc_cat in ["vacancy", "admit_card", "answer_key", "result"]
        html = template_vacancy if is_vacancy else template_generic
        
        html = html.replace("{{JOB_TITLE}}", title)
        html = html.replace("{{TOTAL_VACANCIES}}", str(vacancies))
        html = html.replace("{{FEE_SHORT}}", str(fee)[:30])
        html = html.replace("{{AGE_LIMIT_SHORT}}", str(age)[:30])
        html = html.replace("{{QUAL_SHORT}}", str(qual)[:30])
        html = html.replace("{{NOTICE_REF}}", str(notice_ref))
        html = html.replace("{{ORG_NAME}}", job.get("organization", org_short))
        html = html.replace("{{ORG_SLUG}}", org_slug)
        html = html.replace("{{APPLY_URL}}", apply_url)
        html = html.replace("{{LAST_DATE_FULL}}", "Check Notification")
        html = html.replace("{{LAST_DATE_SHORT}}", "TBD")
        
        with open(page_path, "w", encoding="utf-8") as f:
            f.write(html)
            
        # Index feed
        feed_items.append(f'''
        <a class="register-row" href="{page_url}">
          <div class="register-title">{title}</div>
          <div class="register-meta">
            <span class="register-tag">{org_short}</span>
            <span class="register-tag">{vacancies} posts</span>
          </div>
        </a>''')
        
        # Vacancy feed
        vacancy_cards.append(f'''
        <a class="vacancy-card" href="{page_url}" data-category="central" data-state="all-india" data-qualification="{slugify(qual)}" data-vacancies="{vacancies}" data-days-left="30" data-fee="0">
          <div class="vacancy-main">
            <div class="vacancy-title">{title}</div>
            <div class="vacancy-tags">
              <span class="vacancy-tag">{org_short}</span>
            </div>
          </div>
          <div class="vacancy-stats">
            <div class="vacancy-stat"><div class="vacancy-stat-num">{vacancies}</div><div class="vacancy-stat-label">Posts</div></div>
            <div class="vacancy-stat"><div class="vacancy-stat-num">TBD</div><div class="vacancy-stat-label">Left to apply</div></div>
          </div>
        </a>''')
        
        # Org feed
        if org_slug not in org_feeds:
            org_feeds[org_slug] = []
            
        org_feeds[org_slug].append(f'''
        <a class="org-row" href="{page_url}">
          <span class="org-row-title">{title}</span>
          <span class="org-row-meta">New</span>
        </a>''')

    # Update global feeds
    update_html_feed("index.html", "<!-- LATEST_FEED_START -->", "<!-- LATEST_FEED_END -->", "".join(feed_items))
    update_html_feed("vacancy.html", "<!-- VACANCY_FEED_START -->", "<!-- VACANCY_FEED_END -->", "".join(vacancy_cards))
    
    # Update org pages
    for org_slug, rows in org_feeds.items():
        org_file = f"organization-{org_slug}.html"
        if os.path.exists(org_file):
            # Injecting into the Vacancies section
            with open(org_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Since we didn't add markers to org pages, let's inject after the type-section-head of Vacancies
            # Remove the empty-section if it exists
            content = re.sub(r'<div class="empty-section">No active vacancies currently for this organization.</div>', '', content)
            
            # Add markers if not present
            marker_start = "<!-- ORG_VACANCY_START -->"
            marker_end = "<!-- ORG_VACANCY_END -->"
            if marker_start not in content:
                # Find the end of type-section-head for Vacancies
                pattern = r'(<div class="type-section-title">Vacancies <span class="type-count-badge">.*?</span></div>\s*<a class="type-section-link"[^>]*>View all &rarr;</a>\s*</div>)'
                content = re.sub(pattern, rf'\1\n{marker_start}\n{marker_end}', content)
                
            # Now update it
            pattern2 = re.compile(rf'({re.escape(marker_start)}).*?({re.escape(marker_end)})', re.DOTALL)
            content = pattern2.sub(rf'\1\n' + "".join(rows) + rf'\n\2', content)
            
            # Update badge
            content = re.sub(r'(<div class="type-section-title">Vacancies <span class="type-count-badge">)\d+ (active</span></div>)', rf'\g<1>{len(rows)} \g<2>', content)
            
            with open(org_file, "w", encoding="utf-8") as f:
                f.write(content)

    print(f"✅ Generated {len(active_jobs)} HTML pages.")
    print(f"✅ Updated index.html and vacancy.html feeds.")
    print(f"✅ Updated {len(org_feeds)} organization pages.")

if __name__ == "__main__":
    main()
