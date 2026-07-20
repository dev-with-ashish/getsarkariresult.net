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

def download_pdf(url):
    """Downloads a PDF to a temporary file and returns the file path."""
    try:
        # Create a temp file
        fd, path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        # Disable SSL verification for govt sites
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(req, context=ctx, timeout=30) as response, open(path, 'wb') as out_file:
            out_file.write(response.read())
            
        return path
    except Exception as e:
        logger.error(f"Failed to download PDF from {url}: {e}")
        return None

def extract_text_from_pdf(pdf_path):
    """Extracts raw text from a PDF file."""
    try:
        reader = PdfReader(pdf_path)
        text = ""
        # Only read the first 5 pages to save tokens and because fees/dates are usually at the top
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        logger.error(f"Failed to extract text from {pdf_path}: {e}")
        return ""

def parse_pdf_with_ai(pdf_url):
    """
    Downloads the PDF, extracts text, and uses Gemini to parse structured data.
    Returns a dict with applicationFee, ageLimit, totalVacancies, importantDates.
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
        "documentCategory": "Categorize the document strictly as one of: 'vacancy', 'admit_card', 'answer_key', 'result', or 'other'. Use 'other' for generic notices, statistical reports, rules, etc.",
        "applicationFee": "Extract the fee details. E.g. 'General/OBC: ₹100, SC/ST: Nil'",
        "ageLimit": "Extract the minimum and maximum age limit and the cutoff date. E.g. '18-27 Years as on 01/08/2026'",
        "totalVacancies": "Extract the total number of vacancies. Return an integer, or null if not found.",
        "categoryWiseVacancies": "Extract breakdown if available. E.g. 'UR: 50, OBC: 20, SC: 10'",
        "importantDates": {
            "applicationBegin": "YYYY-MM-DD",
            "lastDate": "YYYY-MM-DD"
        },
        "qualifications": ["list", "of", "educational", "qualifications"],
        "selectionProcess": "Brief summary of the selection process (e.g. 'Written Exam, Physical Test, Interview')",
        "payScale": "Extract the salary or pay level. E.g. 'Level-6 (Rs. 35,400 - 1,12,400)'"
    }
    
    If you cannot find a specific field, return null for it.
    
    PDF Text:
    \"\"\"
    """ + text[:15000] + "\n\"\"\"" # Limit to 15k chars to avoid token limits
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        
        # Clean up possible markdown wrappers
        if result_text.startswith("```json"):
            result_text = result_text.replace("```json", "", 1)
        if result_text.endswith("```"):
            result_text = result_text[:-3]
            
        data = json.loads(result_text.strip())
        return data
    except Exception as e:
        logger.error(f"Failed to parse PDF with Gemini: {e}")
        return None

if __name__ == "__main__":
    # Test script
    logging.basicConfig(level=logging.INFO)
    
    # Load .env manually for testing
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                if line.startswith("GEMINI_API_KEY="):
                    os.environ["GEMINI_API_KEY"] = line.strip().split("=", 1)[1]
                    
    test_url = "https://jssc.jharkhand.gov.in/sites/default/files/Brochure%20JILCCE-2026.pdf" 
    print("Testing AI parser on real JSSC Job PDF...")
    res = parse_pdf_with_ai(test_url)
    print("\n--- AI EXTRACTION RESULT ---")
    print(json.dumps(res, indent=2) if res else "Failed or no API key.")
