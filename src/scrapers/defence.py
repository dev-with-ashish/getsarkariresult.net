"""
Defence Recruitment Scraper
============================
Covers:
  - Indian Army (joinindianarmy.nic.in)
  - Indian Navy (joinindiannavy.gov.in)
  - Indian Air Force (agniveervayu.cdac.in / indianairforce.nic.in)
"""

import sys
import os
import json
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from base import BaseScraper, generate_id, parse_date, clean_text, make_absolute_url

from bs4 import BeautifulSoup


class DefenceScraper(BaseScraper):
    """Scrapes defence recruitment websites."""

    SOURCES = [
        {
            "name": "Indian Army",
            "short": "ARMY",
            "url": "https://joinindianarmy.nic.in",
            "branch": "army",
        },
        {
            "name": "Indian Navy",
            "short": "NAVY",
            "url": "https://www.joinindiannavy.gov.in",
            "branch": "navy",
        },
        {
            "name": "Indian Air Force",
            "short": "IAF",
            "url": "https://indianairforce.nic.in",
            "branch": "airforce",
        },
    ]

    def __init__(self):
        super().__init__("defence", "https://joinindianarmy.nic.in")

    def scrape(self):
        all_results = []

        for source in self.SOURCES:
            try:
                results = self._scrape_source(source)
                all_results.extend(results)
            except Exception as e:
                self.logger.warning(f"Error scraping {source['name']}: {e}")

        return all_results

    def _scrape_source(self, source):
        """Scrape a defence recruitment site."""
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
                    "agniveer", "recruitment", "rally", "entry",
                    "officer", "sailor", "airman", "tradesman",
                    "havildar", "naib subedar", "soldier",
                    "nda", "cds", "ota", "afcat", "inet",
                    "notification", "vacancy", "result", "admit",
                    "application", "registration",
                ])

                if not is_relevant:
                    continue

                seen_titles.add(title)
                link_url = make_absolute_url(source["url"], href)
                is_pdf = link_url and link_url.lower().endswith(".pdf")

                notification = {
                    "id": generate_id(f"defence-{source['branch']}", title),
                    "title": f"[{source['short']}] {title}",
                    "organization": source["name"],
                    "organizationShort": source["short"],
                    "category": "central",
                    "subcategory": "defence",
                    "branch": source["branch"],
                    "notificationType": self._categorize(title),
                    "totalVacancies": self._extract_vacancies(title),
                    "qualifications": [],
                    "ageLimit": None,
                    "importantDates": {},
                    "applicationFee": None,
                    "links": {
                        "notification": link_url if is_pdf else None,
                        "detailPage": link_url if not is_pdf else None,
                        "officialWebsite": source["url"],
                    },
                    "source": source["url"].replace("https://", "").replace("http://", ""),
                    "sourceType": "html",
                    "confidence": 0.75,
                    "status": "active",
                }
                results.append(notification)
            except Exception as e:
                self.logger.debug(f"Error parsing defence link: {e}")

        return results

    def _categorize(self, title):
        t = title.lower()
        if "result" in t:
            return "result"
        elif "admit" in t:
            return "admit_card"
        elif any(kw in t for kw in ["recruitment", "rally", "entry", "notification", "vacancy"]):
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
    scraper = DefenceScraper()
    result = scraper.run()
    print(f"\nStatus: {result['status']}, Items: {result['total_items']}, Time: {result['elapsed_seconds']}s")
    for item in result["items"][:10]:
        print(f"  📋 {item['title'][:100]}")
