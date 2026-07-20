import re
import os

# 1. Update pdf_parser.py
with open("src/pdf_parser.py", "r") as f:
    pdf_code = f.read()

new_prompt = """    Required JSON structure:
    {
        "documentCategory": "Categorize the document strictly as one of: 'vacancy', 'admit_card', 'answer_key', 'result', or 'other'. Use 'other' for generic notices, statistical reports, rules, etc.",
        "applicationFee":"""

pdf_code = pdf_code.replace('    Required JSON structure:\n    {\n        "applicationFee":', new_prompt)

with open("src/pdf_parser.py", "w") as f:
    f.write(pdf_code)


# 2. Update index.py
with open("src/index.py", "r") as f:
    idx_code = f.read()

insertion = """                            if enriched_data.get('documentCategory'):
                                job['documentCategory'] = enriched_data['documentCategory']
                            job['applicationFee']"""

idx_code = idx_code.replace("                            job['applicationFee']", insertion)

with open("src/index.py", "w") as f:
    f.write(idx_code)


# 3. Create template-generic.html
with open("job-details.html", "r") as f:
    gen_html = f.read()

# Remove stat row
gen_html = re.sub(r'<div class="stat-row">.*?</div>', '', gen_html, flags=re.DOTALL)
# Change Apply button
gen_html = gen_html.replace('Apply Online &#8599;', 'View Official Document &#8599;')
# Remove everything from Important Dates downwards
gen_html = re.sub(r'<!-- ===== IMPORTANT DATES ===== -->.*(</main>)', r'''
  <div class="eligibility-summary" style="margin-top: 30px;">
    <strong>Official Notice:</strong> This document is a generic notification, statistical report, rule update, or other official communication from the department. Please refer to the official document linked above for complete details.
  </div>
\1''', gen_html, flags=re.DOTALL)

with open("template-generic.html", "w") as f:
    f.write(gen_html)


# 4. Update build_html.py
with open("src/build_html.py", "r") as f:
    build_code = f.read()

build_code = build_code.replace('''    try:
        with open("job-details.html", "r", encoding="utf-8") as f:
            template = f.read()
    except FileNotFoundError:
        print("job-details.html template not found")
        return''', '''    try:
        with open("job-details.html", "r", encoding="utf-8") as f:
            template_vacancy = f.read()
        with open("template-generic.html", "r", encoding="utf-8") as f:
            template_generic = f.read()
    except FileNotFoundError:
        print("Templates not found")
        return''')

build_loop_update = '''
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
        
        html = html.replace("{{JOB_TITLE}}", title)'''

build_code = re.sub(r'\s*notice_ref = job\.get\("id"\)\s*html = template\s*html = html\.replace\("{{JOB_TITLE}}", title\)', build_loop_update, build_code)

with open("src/build_html.py", "w") as f:
    f.write(build_code)

print("All patched successfully!")
