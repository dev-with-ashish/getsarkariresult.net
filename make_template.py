import re

with open("template-job.html", "r") as f:
    content = f.read()

# Make it a clean template
replacements = [
    ("RRB NTPC Recruitment 2026", "{{JOB_TITLE}}"),
    ("6,557 Posts", "{{TOTAL_VACANCIES}} Posts"),
    ("6,557", "{{TOTAL_VACANCIES}}"),
    ("15 Aug 2026", "{{LAST_DATE_FULL}}"),
    ("15 Aug", "{{LAST_DATE_SHORT}}"),
    ("₹500", "{{FEE_SHORT}}"),
    ("18–33", "{{AGE_LIMIT_SHORT}}"),
    ("Graduate", "{{QUAL_SHORT}}"),
    ("CEN 01/2026", "{{NOTICE_REF}}"),
    ("Railway Recruitment Board", "{{ORG_NAME}}"),
    ('href="/rrb/"', 'href="/organization-{{ORG_SLUG}}.html"'),
    ('href="https://www.rrbcdg.gov.in/"', 'href="{{APPLY_URL}}"')
]

for old, new in replacements:
    content = content.replace(old, new)

# Save as job-details.html (the official template)
with open("job-details.html", "w") as f:
    f.write(content)

import os
os.remove("template-job.html")
print("Template created: job-details.html")
