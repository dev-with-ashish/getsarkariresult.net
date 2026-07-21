import os
import tempfile
import urllib.request
import json
import logging
from pypdf import PdfReader
import google.generativeai as genai

logger = logging.getLogger(__name__)

def setup_gemini():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return False
    genai.configure(api_key=api_key)
    return True

def download_pdf_with_playwright(url, path):
    """Uses Playwright to download a PDF, bypassing simple ASP.NET bot blocks."""
    from playwright.sync_api import sync_playwright
    logger.info(f"Fallback: Attempting to download {url} with Playwright...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                accept_downloads=True
            )
            page = context.new_page()
            
            import urllib.parse
            parsed_url = urllib.parse.urlsplit(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # Wait for download event
            try:
                with page.expect_download(timeout=15000) as download_info:
                    try:
                        # Sometimes setting the referer to the homepage bypasses the block
                        page.goto(url, referer=base_url)
                    except Exception as e:
                        if "Download is starting" not in str(e):
                            raise e
                download = download_info.value
                download.save_as(path)
                browser.close()
                return path
            except Exception as e:
                # If no download triggered (timeout), maybe it loaded inline
                try:
                    response = page.goto(url, referer=base_url, wait_until="domcontentloaded")
                    if response:
                        content = response.body()
                        if b"%PDF-" in content[:1024]:
                            with open(path, 'wb') as f:
                                f.write(content)
                            browser.close()
                            return path
                except Exception as e2:
                    logger.warning(f"Playwright inline load failed: {e2}")
            
            logger.warning(f"Playwright: No PDF content found at {url}")
            browser.close()
            return None
    except Exception as e:
        logger.error(f"Playwright fallback failed for {url}: {e}")
        return None

def is_html(path):
    """Checks if a file is an HTML document instead of a PDF."""
    try:
        with open(path, 'rb') as f:
            header = f.read(512).decode('utf-8', errors='ignore').lower()
            return "<html" in header or "<!doctype" in header
    except Exception:
        return False

def download_pdf(url):
    """Downloads a PDF to a temporary file and returns the file path."""
    try:
        import urllib.parse
        # Safely encode paths that contain spaces or special chars
        parsed = urllib.parse.urlsplit(url)
        safe_path = urllib.parse.quote(parsed.path)
        safe_url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, safe_path, parsed.query, parsed.fragment))

        fd, path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        
        req = urllib.request.Request(safe_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(req, context=ctx, timeout=30) as response, open(path, 'wb') as out_file:
            out_file.write(response.read())
            
        # Check if the site returned an HTML page (bot block) instead of a PDF
        if is_html(path):
            logger.warning(f"Site returned HTML instead of PDF for {url}. Triggering fallback.")
            playwright_path = download_pdf_with_playwright(safe_url, path)
            if playwright_path and not is_html(playwright_path):
                return playwright_path
            return None
            
        return path
    except Exception as e:
        logger.warning(f"Standard download failed for {url}: {e}. Triggering fallback.")
        fd, path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        playwright_path = download_pdf_with_playwright(url, path)
        if playwright_path and not is_html(playwright_path):
            return playwright_path
        return None

def extract_text_from_pdf(pdf_path):
    """Extracts raw text from a PDF file."""
    try:
        reader = PdfReader(pdf_path)
        text = ""
        # Read the whole PDF (Gemini 2.5 Flash has a massive 1M token limit)
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        logger.error(f"Failed to extract text from {pdf_path}: {e}")
        return ""

def parse_pdf_with_ai(pdf_url):
    """
    Downloads the PDF, extracts text, and uses Gemini to parse structured data.
    """
    if not setup_gemini():
        logger.warning("GEMINI_API_KEY not found. Skipping AI PDF parsing.")
        return None
        
    pdf_path = download_pdf(pdf_url)
    if not pdf_path:
        return None
        
    text = extract_text_from_pdf(pdf_path)
    os.remove(pdf_path) # Cleanup
    
    if not text or len(text.strip()) < 50:
        logger.warning(f"Extracted text is too short or empty for {pdf_url}")
        return None
        
    prompt = """
    You are an expert data extractor for Indian Government Jobs.
    Read the following text extracted from an official recruitment notification PDF.
    Extract the following information and return ONLY a valid JSON object. Do not wrap in markdown blocks, just raw JSON.
    
    Required JSON structure:
    {
        "documentCategory": "Categorize the document strictly as one of: 'vacancy', 'admit_card', 'answer_key', 'result', or 'other'. CRITICAL INSTRUCTION: If the document announces a RESULT, PROVISIONAL PANEL, or SHORTLIST of selected candidates, you MUST use 'result'. If it is an ADMIT CARD, use 'admit_card'. ONLY use 'vacancy' if the document is an INITIAL recruitment notification actively inviting NEW applications with an open application window. If it is none of these (e.g. a generic notice, date extension, syllabus, or an amendment), strictly fallback to 'other'. Do NOT default to 'vacancy'.",
        "categorySubtitle": "A short 3-6 word subtitle describing the specific posts or department. E.g. 'Paramedical Categories' or 'Group D Posts'",
        
        "applicationFee": "Extract a short fee summary (e.g. '₹500')",
        "applicationFeeDetails": {"General/OBC": "₹500", "SC/ST": "₹250"},
        "feeNote": "Any note about fee refunds or payment methods.",
        
        "ageLimit": "Short summary (e.g. '18-33 Years')",
        "ageLimitDetails": {"Minimum Age": "18 Years", "Maximum Age": "33 Years", "Age Reckoned As On": "01 Jan 2027", "OBC Relaxation": "+3 Years", "SC/ST Relaxation": "+5 Years"},
        
        "totalVacancies": "Integer total number of vacancies. Return null if not found.",
        "vacancyBreakdown": {"General": "100", "OBC": "50", "SC": "30", "ST": "15"},
        
        "importantDates": {
            "Notification Released": "YYYY-MM-DD",
            "Application Start": "YYYY-MM-DD",
            "Last Date to Apply": "YYYY-MM-DD"
        },
        
        "eligibilitySummary": "A short 1-2 sentence paragraph summarizing the eligibility.",
        "eligibilityDetails": {"Educational Qualification": "Bachelor's degree", "Nationality": "Indian Citizen"},
        
        "selectionProcess": ["Computer Based Test (CBT) - Stage 1", "Document Verification", "Medical Examination"],
        "payScale": "Extract the salary or pay level. E.g. 'Level-6 (Rs. 35,400 - 1,12,400)'"
    }
    
    If you cannot find a specific field or detail, omit the key or return null.
    
    PDF Text:
    \"\"\"
    """ + text[:300000] + "\n\"\"\"" # 300k chars is plenty safe and grabs almost all docs
    
    import time
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = model.generate_content(prompt)
                result_text = response.text.strip()
                
                if result_text.startswith("```json"):
                    result_text = result_text.replace("```json", "", 1)
                if result_text.endswith("```"):
                    result_text = result_text[:-3]
                    
                data = json.loads(result_text.strip())
                
                # Sleep 5 seconds to respect the 15 RPM free tier limit
                time.sleep(5) 
                return data
            except Exception as inner_e:
                error_str = str(inner_e)
                if "429" in error_str:
                    logger.warning(f"Rate limited (429) on attempt {attempt+1}/{max_retries}. Sleeping 10s...")
                    time.sleep(10)
                else:
                    raise inner_e
                    
    except Exception as e:
        logger.error(f"Failed to parse PDF with Gemini: {e}")
        return None

if __name__ == "__main__":
    pass
