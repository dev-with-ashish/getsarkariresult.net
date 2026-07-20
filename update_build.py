import re

with open("src/build_html.py", "r", encoding="utf-8") as f:
    build_code = f.read()

# Fix Title
build_code = build_code.replace(
    'title = job.get("title", "Job Update")',
    'title = job.get("title", "Job Update").replace("Click to know Update", "").strip()'
)

# New Replacements block
new_replacement_logic = '''
        html = html.replace("{{JOB_TITLE}}", title)
        html = html.replace("{{TOTAL_VACANCIES}}", str(vacancies))
        html = html.replace("{{FEE_SHORT}}", str(fee)[:30])
        html = html.replace("{{AGE_LIMIT_SHORT}}", str(age)[:30])
        html = html.replace("{{QUAL_SHORT}}", str(qual)[:30])
        html = html.replace("{{NOTICE_REF}}", str(notice_ref))
        html = html.replace("{{ORG_NAME}}", job.get("organization", org_short))
        html = html.replace("{{ORG_SLUG}}", org_slug)
        html = html.replace("{{APPLY_URL}}", apply_url)
        
        # New Detailed AI Fields
        html = html.replace("{{CATEGORY_SUBTITLE}}", job.get("categorySubtitle") or "Notification details")
        html = html.replace("{{ELIGIBILITY_SUMMARY}}", job.get("eligibilitySummary") or "Please check the official notification for complete eligibility details.")
        html = html.replace("{{FEE_NOTE}}", job.get("feeNote") or "")
        
        pdf_url = job.get("links", {}).get("notification") or apply_url
        html = html.replace("{{NOTIFICATION_PDF_URL}}", pdf_url)
        
        # Important Dates Table
        dates = job.get("importantDates", {})
        if not dates:
            dates = {"Notification": "See Official PDF"}
        dates_html = "".join([f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in dates.items()])
        html = html.replace("{{IMPORTANT_DATES_ROWS}}", dates_html)
        
        # Application Fee Table
        fee_details = job.get("applicationFeeDetails", {})
        if not fee_details:
            fee_details = {"General": fee}
        fee_html = "".join([f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in fee_details.items()])
        html = html.replace("{{APPLICATION_FEE_ROWS}}", fee_html)
        
        # Age Limit Table
        age_details = job.get("ageLimitDetails", {})
        if not age_details:
            age_details = {"Age Limit": age}
        age_html = "".join([f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in age_details.items()])
        html = html.replace("{{AGE_LIMIT_ROWS}}", age_html)
        
        # Vacancy Breakdown Table
        vac_details = job.get("vacancyBreakdown", {})
        if not vac_details:
            vac_details = {"Total": str(vacancies)}
        vac_html = "".join([f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in vac_details.items()])
        html = html.replace("{{VACANCY_BREAKDOWN_ROWS}}", vac_html)
        
        # Eligibility Rows
        elig_details = job.get("eligibilityDetails", {})
        if not elig_details:
            elig_details = {"Qualification": qual}
        elig_html = "".join([f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in elig_details.items()])
        html = html.replace("{{ELIGIBILITY_ROWS}}", elig_html)
        
        # Selection Process
        steps = job.get("selectionProcess", [])
        if not steps:
            steps = ["Check Notification"]
        if isinstance(steps, str):
            steps = [steps]
        step_html = "".join([f"<li>{s}</li>" for s in steps])
        html = html.replace("{{SELECTION_PROCESS_ROWS}}", step_html)
'''

# We need to replace the old replace block.
old_block_pattern = re.compile(r'        html = html.replace\("{{JOB_TITLE}}", title\).*?html = html.replace\("{{LAST_DATE_SHORT}}", "TBD"\)', re.DOTALL)

build_code = old_block_pattern.sub(new_replacement_logic.strip(), build_code)

with open("src/build_html.py", "w", encoding="utf-8") as f:
    f.write(build_code)

print("build_html.py updated!")
