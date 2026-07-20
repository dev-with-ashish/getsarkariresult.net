import urllib.request
import re
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://uppsc.up.nic.in"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req, context=ctx).read().decode("utf-8")
js_files = re.findall(r'src="([^"]+\.js[^"]*)"', html)

for js in js_files:
    if not js.startswith("http"):
        js = url + "/" + js.lstrip("/")
    try:
        req = urllib.request.Request(js, headers={"User-Agent": "Mozilla/5.0"})
        content = urllib.request.urlopen(req, context=ctx).read().decode("utf-8", errors="ignore")
        
        endpoints = re.findall(r'[\"\']([^\"\']+\.asmx/[^\"\']+)[\"\']', content)
        apis = re.findall(r'[\"\'](/api/[^\"\']+|api/[^\"\']+)[\"\']', content)
        http_calls = re.findall(r'\$http\.(?:post|get)\([\"\']([^\"\']+)[\"\']', content)
        
        if endpoints or apis or http_calls:
            print(f"\n--- {js} ---")
            for e in set(endpoints): print("ASMX:", e)
            for a in set(apis): print("API:", a)
            for h in set(http_calls): print("$http:", h)
            
    except Exception as e:
        print(f"Error fetching {js}: {e}")
