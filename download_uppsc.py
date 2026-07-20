import requests
url = "https://uppsc.up.nic.in/Open_PDF_DB.aspx?I4PnQ0tBagkKFmHgqmmkW30lDXcVzR9+"
headers = {"User-Agent": "Mozilla/5.0"}
try:
    print(f"Downloading {url}...")
    resp = requests.get(url, headers=headers, verify=False, timeout=30)
    resp.raise_for_status()
    with open("UPPSC_Result.pdf", "wb") as f:
        f.write(resp.content)
    print("Download complete: UPPSC_Result.pdf")
except Exception as e:
    print(f"Failed to download: {e}")
