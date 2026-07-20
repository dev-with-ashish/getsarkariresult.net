import re

with open("src/build_html.py", "r") as f:
    lines = f.readlines()

new_lines = []
in_build_block = False

for i, line in enumerate(lines):
    if line.strip() == 'page_url = f"/{page_path}"':
        new_lines.append('        is_ai_enriched = "documentCategory" in job\n')
        new_lines.append('        apply_url = job.get("links", {}).get("officialWebsite") or "#"\n')
        new_lines.append('        pdf_url = job.get("links", {}).get("notification") or apply_url\n')
        new_lines.append('        page_url = f"/{page_path}" if is_ai_enriched else (pdf_url or apply_url or "#")\n')
        continue
    
    # Remove the old extractions since we moved them up
    if line.strip() == 'apply_url    = job.get("links", {}).get("officialWebsite") or "#"':
        continue
    if line.strip() == 'pdf_url      = job.get("links", {}).get("notification") or apply_url':
        continue

    # Start indenting at stat_row logic
    if line.strip() == 'if doc_cat == "vacancy":' and "stat_row =" in lines[i+1]:
        new_lines.append('        if is_ai_enriched:\n')
        in_build_block = True
    
    # Stop indenting at feed items
    if in_build_block and line.strip() == '# ── Index feed (all active docs) ─────────────────────────────────':
        in_build_block = False
        new_lines.append(line)
        continue
        
    if in_build_block:
        new_lines.append('    ' + line if line.strip() else line)
    else:
        new_lines.append(line)

with open("src/build_html.py", "w") as f:
    f.writelines(new_lines)

print("Patch applied successfully.")
