"""
IBPS (Institute of Banking Personnel Selection) Scraper
========================================================
IBPS runs a server-rendered site at ibps.in (220KB HTML).
Covers banking exams: PO, Clerk, SO, RRB PO/Clerk, etc.
"""

import sys
import os
import json
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from base import BaseScraper, generate_id, parse_date, clean_text, make_absolute_url

from bs4 import BeautifulSoup


class IBPSScraper(BaseScraper):
    """Scrapes ibps.in for banking recruitment notifications."""

    BASE = "https://www.ibps.in"

    def __init__(self):
        super().__init__("ibps", self.BASE)

    def scrape(self):
        results = []

        # Scrape homepage for latest notifications
        homepage = self._scrape_homepage()
        results.extend(homepage)

        return results

    def _scrape_homepage(self):
        """Parse the IBPS homepage for notifications and exam updates."""
        html = self.fetch_html(self.BASE)
        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        results = []
        seen_titles = set()

        # IBPS typically has notifications in tables, marquee, or news sections
        # Look for links with keywords
        all_links = soup.select("a[href]")

        for link in all_links:
            try:
                title = clean_text(link.get_text())
                href = link.get("href", "")

                if not title or len(title) < 10 or title in seen_titles:
                    continue

                # Filter for relevant content
                title_lower = title.lower()
                is_relevant = any(kw in title_lower for kw in [
                    "crp", "po", "clerk", "officer", "specialist",
                    "rrb", "recruitment", "notification", "admit",
                    "result", "score", "vacancy", "application",
                    "online", "exam", "prelim", "mains",
                    "ibps", "bank", "probationary",
                ])

                # Also check href for PDFs and relevant paths
                is_relevant = is_relevant or (
                    href.lower().endswith(".pdf") and
                    any(kw in href.lower() for kw in ["notif", "advt", "recruit", "crp"])
                )

                if not is_relevant:
                    continue

                seen_titles.add(title)
                link_url = make_absolute_url(self.BASE, href)
                is_pdf = link_url and link_url.lower().endswith(".pdf")

                notification = {
                    "id": generate_id("ibps", title),
                    "title": title,
                    "organization": "Institute of Banking Personnel Selection (IBPS)",
                    "organizationShort": "IBPS",
                    "category": "central",
                    "subcategory": "banking",
                    "notificationType": self._categorize(title),
                    "totalVacancies": self._extract_vacancies(title),
                    "qualifications": ["Graduate"],  # Most IBPS exams need graduation
                    "ageLimit": None,
                    "importantDates": {},
                    "applicationFee": None,
                    "links": {
                        "notification": link_url if is_pdf else None,
                        "detailPage": link_url if not is_pdf else None,
                        "officialWebsite": self.BASE,
                    },
                    "source": "ibps.in",
                    "sourceType": "html",
                    "confidence": 0.80,
                    "status": "active",
                }

                results.append(notification)
            except Exception as e:
                self.logger.debug(f"Error parsing IBPS link: {e}")

        return results

    def _categorize(self, title):
        """Categorize IBPS notification."""
        t = title.lower()
        if any(kw in t for kw in ["result", "score", "marks"]):
            return "result"
        elif any(kw in t for kw in ["admit card", "call letter"]):
            return "admit_card"
        elif any(kw in t for kw in ["answer key"]):
            return "answer_key"
        elif any(kw in t for kw in ["recruitment", "notification", "advt", "crp", "application"]):
            return "recruitment"
        return "notification"

    def _extract_vacancies(self, title):
        """Extract vacancy count from title."""
        match = re.search(r"(\d+)\s*(?:posts?|vacancies)", title, re.IGNORECASE)
        if match:
            count = int(match.group(1))
            if 1 <= count <= 100000:
                return count
        return None


# Standalone test
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    scraper = IBPSScraper()
    result = scraper.run()
    print(f"\nStatus: {result['status']}, Items: {result['total_items']}, Time: {result['elapsed_seconds']}s")
    for item in result["items"][:10]:
        print(f"  📋 {item['title'][:100]}")
