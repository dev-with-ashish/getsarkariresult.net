import re

def fix_template(filepath, is_generic):
    with open(filepath, "r") as f:
        html = f.read()

    # Fix title tag
    html = re.sub(r'<title>.*?</title>', r'<title>{{JOB_TITLE}} | getsarkariresult.net</title>', html)
    
    # Fix meta description
    html = re.sub(r'<meta name="description" content="[^"]*">', r'<meta name="description" content="Official update for {{JOB_TITLE}} by {{ORG_NAME}}.">', html)
    
    # Strip the hardcoded JobPosting JSON-LD entirely if it's generic, or parameterize it if it's vacancy
    if is_generic:
        # Remove JobPosting schema
        html = re.sub(r'<script type="application/ld\+json">\s*{\s*"@context": "https://schema\.org",\s*"@type": "JobPosting".*?</script>', '', html, flags=re.DOTALL)
    else:
        # Very rough parameterization of JobPosting
        html = re.sub(r'"title": "[^"]*"', r'"title": "{{JOB_TITLE}}"', html)
        html = re.sub(r'"description": "[^"]*"', r'"description": "Recruitment for {{JOB_TITLE}} by {{ORG_NAME}}."', html)
        html = re.sub(r'"value": "90b039f30407"', r'"value": "{{NOTICE_REF}}"', html)
        html = re.sub(r'"name": "Railway Recruitment Board \(RRB\)"', r'"name": "{{ORG_NAME}}"', html)
        html = re.sub(r'"totalJobOpenings": \d+', r'"totalJobOpenings": "{{TOTAL_VACANCIES}}"', html)
        
    # Fix breadcrumb JSON-LD
    html = re.sub(r'\{ "@type": "ListItem", "position": 3, "name": "[^"]*", "item": "https://getsarkariresult\.net/[^"]*" \}',
                  r'{ "@type": "ListItem", "position": 3, "name": "{{JOB_TITLE}}", "item": "https://getsarkariresult.net/{{ORG_SLUG}}/2026/{{NOTICE_REF}}" }', html)

    with open(filepath, "w") as f:
        f.write(html)

fix_template("job-details.html", False)
fix_template("template-generic.html", True)
print("Meta tags and schemas parameterized!")
