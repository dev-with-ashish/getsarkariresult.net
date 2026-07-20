"""
Railway Recruitment Board (RRB) Scraper
========================================
RRBs manage railway recruitment across India.
The main site rrbcdg.gov.in can be unreliable, so we also
scrape regional RRB sites and the Railway SECR page.
"""

import sys
import os
import json
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from base import BaseScraper, generate_id, parse_date, clean_text, make_absolute_url

from bs4 import BeautifulSoup


class RailwayScraper(BaseScraper):
    """Scrapes Railway Recruitment Board sites for NTPC, Group D, ALP, etc."""

    # All 21 Regional RRB sources to guarantee 100% regional and national coverage
    SOURCES = [
        {"name": "RRB Ahmedabad", "url": "https://www.rrbahmedabad.gov.in/"},
        {"name": "RRB Ajmer", "url": "https://rrbajmer.gov.in/"},
        {"name": "RRB Allahabad", "url": "https://rrbald.gov.in/"},
        {"name": "RRB Bangalore", "url": "https://www.rrbbnc.gov.in/"},
        {"name": "RRB Bhopal", "url": "https://rrbbhopal.gov.in/"},
        {"name": "RRB Bhubaneswar", "url": "https://www.rrbbbs.gov.in/"},
        {"name": "RRB Bilaspur", "url": "https://www.rrbbilaspur.gov.in/"},
        {"name": "RRB Chandigarh", "url": "https://www.rrbcdg.gov.in/"},
        {"name": "RRB Chennai", "url": "https://www.rrbchennai.gov.in/"},
        {"name": "RRB Gorakhpur", "url": "https://www.rrbgkp.gov.in/"},
        {"name": "RRB Guwahati", "url": "https://www.rrbguwahati.gov.in/"},
        {"name": "RRB Jammu-Srinagar", "url": "https://www.rrbjammu.nic.in/"},
        {"name": "RRB Kolkata", "url": "https://www.rrbkolkata.gov.in/"},
        {"name": "RRB Malda", "url": "https://www.rrbmalda.gov.in/"},
        {"name": "RRB Mumbai", "url": "https://www.rrbmumbai.gov.in/"},
        {"name": "RRB Muzaffarpur", "url": "https://www.rrbmuzaffarpur.gov.in/"},
        {"name": "RRB Patna", "url": "https://www.rrbpatna.gov.in/"},
        {"name": "RRB Ranchi", "url": "https://www.rrbranchi.gov.in/"},
        {"name": "RRB Secunderabad", "url": "https://rrbsecunderabad.gov.in/"},
        {"name": "RRB Siliguri", "url": "https://www.rrbsiliguri.gov.in/"},
        {"name": "RRB Thiruvananthapuram", "url": "https://rrbthiruvananthapuram.gov.in/"},
        {"name": "Indian Railways (Central)", "url": "https://indianrailways.gov.in/railwayboard/view_section.jsp?lang=0&id=0,1,304,366,554"},
    ]

    def __init__(self):
        super().__init__("railway", "https://www.rrbcdg.gov.in")

    def scrape(self):
        """Scrape RRB sites for notifications."""
        all_results = []

        for source in self.SOURCES:
            try:
                results = self._scrape_source(source)
                all_results.extend(results)
            except Exception as e:
                self.logger.warning(f"Error scraping {source['name']}: {e}")

        return all_results

    def _scrape_source(self, source):
        """Scrape a single RRB source."""
        html = self.fetch_html(source["url"], timeout=15)
        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        results = []
        seen_titles = set()

        all_links = soup.select("a[href]")
        for link in all_links:
            try:
                title = clean_text(link.get_text())
                href = link.get("href", "")

                if not title or len(title) < 10 or title in seen_titles:
                    continue

                title_lower = title.lower()
                is_relevant = any(kw in title_lower for kw in [
                    "ntpc", "group d", "alp", "technician", "level",
                    "recruitment", "vacancy", "notification", "result",
                    "admit", "rrb", "rrc", "railway", "cen",
                    "ministerial", "isolated", "paramedical",
                ]) or (href.lower().endswith(".pdf") and "rrb" in href.lower())

                if not is_relevant:
                    continue

                seen_titles.add(title)
                link_url = make_absolute_url(source["url"], href)
                is_pdf = link_url and link_url.lower().endswith(".pdf")

                notification = {
                    "id": generate_id("railway", title),
                    "title": title,
                    "organization": "Railway Recruitment Board (RRB)",
                    "organizationShort": "RRB",
                    "category": "central",
                    "subcategory": "railway",
                    "notificationType": self._categorize(title),
                    "totalVacancies": self._extract_vacancies(title),
                    "qualifications": [],
                    "ageLimit": None,
                    "importantDates": {},
                    "applicationFee": None,
                    "links": {
                        "notification": link_url if is_pdf else None,
                        "detailPage": link_url if not is_pdf else None,
                        "officialWebsite": "https://www.rrbcdg.gov.in",
                    },
                    "source": source["url"].replace("https://", "").replace("http://", "").split("/")[0],
                    "sourceType": "html",
                    "confidence": 0.75,
                    "status": "active",
                }
                results.append(notification)
            except Exception as e:
                self.logger.debug(f"Error parsing railway link: {e}")

        return results

    def _categorize(self, title):
        t = title.lower()
        if any(kw in t for kw in ["result", "score", "merit"]):
            return "result"
        elif any(kw in t for kw in ["admit card", "e-call"]):
            return "admit_card"
        elif any(kw in t for kw in ["answer key"]):
            return "answer_key"
        elif any(kw in t for kw in ["recruitment", "cen", "notification", "vacancy"]):
            return "recruitment"
        return "notification"

    def _extract_vacancies(self, title):
        match = re.search(r"(\d+)\s*(?:posts?|vacancies)", title, re.IGNORECASE)
        if match:
            count = int(match.group(1))
            if 1 <= count <= 500000:
                return count
        return None


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    scraper = RailwayScraper()
    result = scraper.run()
    print(f"\nStatus: {result['status']}, Items: {result['total_items']}, Time: {result['elapsed_seconds']}s")
    for item in result["items"][:10]:
        print(f"  📋 {item['title'][:100]}")
