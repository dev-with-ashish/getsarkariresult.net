import re

with open("job-details.html", "r", encoding="utf-8") as f:
    html = f.read()

# 1. Subtitle Category
html = re.sub(
    r'<p class="page-sub">Non-Technical Popular Categories &middot;', 
    r'<p class="page-sub">{{CATEGORY_SUBTITLE}} &middot;', 
    html
)

# 2. Important Dates Table
dates_table_pattern = r'<div class="section-title">Important dates</div>\s*<table class="data-table">.*?</table>'
dates_table_replacement = r'''<div class="section-title">Important dates</div>
    <table class="data-table">
      {{IMPORTANT_DATES_ROWS}}
    </table>'''
html = re.sub(dates_table_pattern, dates_table_replacement, html, flags=re.DOTALL)

# 3. Application Fee Table
fee_table_pattern = r'<div class="section-title">Application fee</div>\s*<table class="cat-table">.*?</table>\s*<p.*?</p>'
fee_table_replacement = r'''<div class="section-title">Application fee</div>
    <table class="data-table">
      {{APPLICATION_FEE_ROWS}}
    </table>
    <p style="font-size: 11px; color: var(--slate); margin-top: 6px;">{{FEE_NOTE}}</p>'''
html = re.sub(fee_table_pattern, fee_table_replacement, html, flags=re.DOTALL)

# 4. Age Limit Table
age_table_pattern = r'<div class="section-title">Age limit &amp; relaxation</div>\s*<table class="data-table">.*?</table>'
age_table_replacement = r'''<div class="section-title">Age limit &amp; relaxation</div>
    <table class="data-table">
      {{AGE_LIMIT_ROWS}}
    </table>'''
html = re.sub(age_table_pattern, age_table_replacement, html, flags=re.DOTALL)

# 5. Vacancy Breakdown
vac_table_pattern = r'<div class="section-title">Vacancy breakdown</div>\s*<table class="cat-table">.*?</table>'
vac_table_replacement = r'''<div class="section-title">Vacancy breakdown</div>
    <table class="data-table">
      {{VACANCY_BREAKDOWN_ROWS}}
    </table>'''
html = re.sub(vac_table_pattern, vac_table_replacement, html, flags=re.DOTALL)

# 6. Eligibility Summary
eligibility_pattern = r'<div class="section-title">Eligibility</div>\s*<div class="eligibility-summary">.*?</div>\s*<table class="data-table">.*?</table>'
eligibility_replacement = r'''<div class="section-title">Eligibility</div>
    <div class="eligibility-summary">
      {{ELIGIBILITY_SUMMARY}}
    </div>
    <table class="data-table">
      {{ELIGIBILITY_ROWS}}
    </table>'''
html = re.sub(eligibility_pattern, eligibility_replacement, html, flags=re.DOTALL)

# 7. Selection Process
selection_pattern = r'<div class="section-title">Selection process</div>\s*<ol class="step-list">.*?</ol>'
selection_replacement = r'''<div class="section-title">Selection process</div>
    <ol class="step-list">
      {{SELECTION_PROCESS_ROWS}}
    </ol>'''
html = re.sub(selection_pattern, selection_replacement, html, flags=re.DOTALL)

# 8. Download PDF Link
pdf_link_pattern = r'<a class="official-link" href="https://www.rrbcdg.gov.in/uploads/rrb-ntpc-2026-notification.pdf"'
pdf_link_replacement = r'<a class="official-link" href="{{NOTIFICATION_PDF_URL}}"'
html = re.sub(pdf_link_pattern, pdf_link_replacement, html)

with open("job-details.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Template parameterization complete!")
