"""
SSC (Staff Selection Commission) Scraper
=========================================
SSC runs an Angular SPA at ssc.gov.in with exposed JSON APIs.
No headless browser needed — direct API fetch returns clean structured data.

Discovered endpoints:
  - /api/admin/5.1/allExams    → List of all exam types
  - /api/admin/5.1/liveExams   → Currently active exams with dates
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from base import BaseScraper, generate_id, parse_date, clean_text


class SSCScraper(BaseScraper):
    """Scrapes SSC.gov.in via its exposed JSON API endpoints."""

    API_BASE = "https://ssc.gov.in/api"

    # Endpoints discovered from the Angular app's main.js bundle
    ENDPOINTS = {
        "live_exams": "/admin/5.1/liveExams",
        "all_exams": "/admin/5.1/allExams",
    }

    def __init__(self):
        super().__init__("ssc", "https://ssc.gov.in")

    def scrape(self):
        """Fetch live exams and all exams from SSC API."""
        results = []

        # Fetch currently active/live exams (have application dates)
        live_exams = self._fetch_live_exams()
        results.extend(live_exams)

        # Fetch all exam categories for reference
        all_exams = self._fetch_all_exams()

        # Merge any exam metadata from allExams that enriches live exams
        self._enrich_with_exam_metadata(results, all_exams)

        # Also try to scrape the notice board page for notifications
        notices = self._fetch_notice_board()
        results.extend(notices)

        return results

    def _fetch_live_exams(self):
        """Fetch currently active exams with application windows."""
        url = f"{self.API_BASE}{self.ENDPOINTS['live_exams']}"
        data = self.fetch_json(url)

        if not data or data.get("statusCode") != "200":
            self.logger.warning("Failed to fetch live exams from SSC API")
            return []

        exams = data.get("data", [])
        results = []

        for exam in exams:
            try:
                notification = self._parse_live_exam(exam)
                if notification:
                    results.append(notification)
            except Exception as e:
                self.logger.warning(f"Error parsing SSC exam: {e}")
                continue

        return results

    def _parse_live_exam(self, exam):
        """Parse a single live exam entry from the API response."""
        title = clean_text(exam.get("examDescription") or exam.get("examName", ""))
        if not title:
            return None

        exam_code = exam.get("examCode", "")
        exam_year = exam.get("examYear", "")

        # Build dates
        important_dates = {}

        app_start = parse_date(exam.get("applicationStartDate"))
        app_end = parse_date(exam.get("applicationEndDate"))
        exam_date = parse_date(exam.get("examDate"))
        admit_start = parse_date(exam.get("admitCardStartDate"))
        admit_end = parse_date(exam.get("admitCardEndDate"))
        answer_key_start = parse_date(exam.get("answerKeyStartDate"))
        correction_start = parse_date(exam.get("correctionStartDate"))
        correction_end = parse_date(exam.get("correctionEndDate"))

        if app_start:
            important_dates["applyStart"] = app_start
        if app_end:
            important_dates["applyEnd"] = app_end
        if exam_date:
            important_dates["examDate"] = exam_date
        if admit_start:
            important_dates["admitCardStart"] = admit_start
        if admit_end:
            important_dates["admitCardEnd"] = admit_end
        if answer_key_start:
            important_dates["answerKeyStart"] = answer_key_start
        if correction_start:
            important_dates["correctionStart"] = correction_start
        if correction_end:
            important_dates["correctionEnd"] = correction_end

        # Fee information
        application_fee = {}
        if exam.get("fee"):
            application_fee["general"] = exam["fee"]
        if exam.get("cwfee1"):
            application_fee["scStPwdWomen"] = exam["cwfee1"]

        # Build notification PDFs from attachments
        pdf_links = []
        for attachment in exam.get("attachments", []):
            file_server = exam.get("fileServer", "attachment")
            file_name = attachment.get("fileName", "")
            if file_name:
                pdf_url = f"https://ssc.gov.in/api/{file_server}/uploads/masterData/NoticeBoards/{file_name}"
                pdf_links.append({
                    "title": clean_text(attachment.get("title", file_name)),
                    "url": pdf_url,
                })

        # Application link
        nav_url = exam.get("navigationUrl", "")
        if nav_url and nav_url.upper() != "NULL" and nav_url.strip():
            apply_link = f"https://ssc.gov.in{nav_url}"
        else:
            apply_link = "https://ssc.gov.in/apply"

        # Determine status
        status = "active" if exam.get("isActive") else "expired"

        notification = {
            "id": generate_id("ssc", f"{exam_code}-{exam_year}-{title}"),
            "title": title,
            "organization": "Staff Selection Commission (SSC)",
            "organizationShort": "SSC",
            "category": "central",
            "subcategory": "ssc",
            "examCode": exam_code,
            "examYear": exam_year,
            "totalVacancies": None,  # Not in API, needs PDF parsing
            "qualifications": [],
            "ageLimit": self._get_age_limits(exam),
            "importantDates": important_dates,
            "applicationFee": application_fee if application_fee else None,
            "links": {
                "applyOnline": apply_link,
                "officialWebsite": "https://ssc.gov.in",
                "notifications": pdf_links,
            },
            "source": "ssc.gov.in",
            "sourceType": "api",  # Direct API = highest confidence
            "confidence": 0.95,
            "status": status,
            "rawData": {
                "apiId": exam.get("id"),
                "examId": exam.get("examId"),
            },
        }

        return notification

    def _get_age_limits(self, exam):
        """Extract age limits if present in the API response."""
        min_age = exam.get("minAge")
        max_age = exam.get("maxAge")
        if min_age or max_age:
            return {
                "min": min_age,
                "max": max_age,
            }
        return None

    def _fetch_all_exams(self):
        """Fetch the master list of all SSC exam types."""
        url = f"{self.API_BASE}{self.ENDPOINTS['all_exams']}"
        data = self.fetch_json(url)

        if not data or data.get("statusCode") != "200":
            return []

        return data.get("data", [])

    def _enrich_with_exam_metadata(self, results, all_exams):
        """Enrich live exam results with metadata from allExams endpoint."""
        exam_lookup = {}
        for exam in all_exams:
            code = exam.get("examCode", "")
            exam_lookup[code] = {
                "fullName": exam.get("examName", ""),
                "hindiName": exam.get("hExamName", ""),
                "navigationUrl": exam.get("navigationUrl", ""),
            }

        for result in results:
            code = result.get("examCode", "")
            if code in exam_lookup:
                meta = exam_lookup[code]
                if not result.get("links", {}).get("applyOnline") and meta.get("navigationUrl"):
                    result["links"]["applyOnline"] = f"https://ssc.gov.in{meta['navigationUrl']}"

    def _fetch_notice_board(self):
        """
        Try to scrape the SSC notice board page via HTML fallback.
        The notice board API requires auth, so we parse the rendered page.
        """
        html = self.fetch_html("https://ssc.gov.in")
        if not html:
            return []

        # SSC is an Angular SPA — the HTML won't have notice board content
        # without JS rendering. For now, return empty.
        # This will be handled by Playwright in the headless layer.
        return []


# Allow running this scraper standalone for testing
if __name__ == "__main__":
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    scraper = SSCScraper()
    result = scraper.run()

    print(f"\nStatus: {result['status']}")
    print(f"Items found: {result['total_items']}")
    print(f"Time: {result['elapsed_seconds']}s")
    print()

    for item in result["items"]:
        print(f"  📋 {item['title']}")
        dates = item.get("importantDates", {})
        if dates.get("applyStart"):
            print(f"     Apply: {dates['applyStart']} → {dates.get('applyEnd', '?')}")
        if dates.get("examDate"):
            print(f"     Exam: {dates['examDate']}")
        print(f"     Status: {item['status']}")
        print()

    # Also dump full JSON
    print("\n=== Full JSON Output ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))
