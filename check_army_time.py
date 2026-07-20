import urllib.request
import re
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://joinindianarmy.nic.in/default.aspx"
try:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, context=ctx, timeout=15).read().decode("utf-8")
    
    # Look for JAG
    matches = re.finditer(r".{0,100}JAG.{0,100}", html, re.IGNORECASE)
    found = False
    for m in matches:
        print("Found HTML surrounding JAG:", m.group(0))
        found = True
        
    if not found:
        print("Could not find JAG on the homepage. Let's try Officers Entry page...")
        url = "https://joinindianarmy.nic.in/alpha/officers-notifications.htm"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, context=ctx, timeout=15).read().decode("utf-8")
        matches = re.finditer(r".{0,100}JAG.{0,100}", html, re.IGNORECASE)
        for m in matches:
            print("Found HTML surrounding JAG on Officers page:", m.group(0))
            
    # Extract any PDF links matching JAG
    pdf_links = re.findall(r"href=[\"']([^\"']*JAG[^\"']*\.pdf)[\"']", html, re.IGNORECASE)
    for link in set(pdf_links):
        print("\nFound PDF link:", link)
        if not link.startswith("http"):
            link = "https://joinindianarmy.nic.in" + (link if link.startswith("/") else "/" + link)
        
        # Check Last-Modified header
        try:
            head_req = urllib.request.Request(link, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(head_req, context=ctx, timeout=10)
            print("Last-Modified for PDF:", resp.headers.get("Last-Modified"))
        except Exception as e:
            print("Could not get HEAD for PDF:", e)
            
except Exception as e:
    print("Error fetching site:", e)
