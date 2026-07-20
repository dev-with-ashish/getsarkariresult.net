"""
State PSC Scrapers
===================
Covers major state public service commissions:
  - UPPSC (Uttar Pradesh)
  - BPSC (Bihar)
  - MPPSC (Madhya Pradesh)
  - RPSC (Rajasthan)

All are server-rendered HTML sites — standard HTTP + BeautifulSoup parsing.
"""

import sys
import os
import json
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from base import BaseScraper, generate_id, parse_date, clean_text, make_absolute_url

from bs4 import BeautifulSoup


class StatePSCScraper(BaseScraper):
    """
    Generic State PSC scraper that handles multiple state commissions.
    Each state has slightly different HTML structure, handled via config.
    """

    # State PSC configurations
    STATES = {
        "uppsc": {
            "name": "Uttar Pradesh Public Service Commission",
            "short": "UPPSC",
            "base_url": "https://uppsc.up.nic.in",
            "pages": ["/", "/CandidatePages/NotificationsandAdvertisements/Notifications.aspx"],
            "state": "Uttar Pradesh",
        },
        "bpsc": {
            "name": "Bihar Public Service Commission",
            "short": "BPSC",
            "base_url": "https://www.bpsc.bih.nic.in",
            "pages": ["/"],
            "state": "Bihar",
        },
        "mppsc": {
            "name": "Madhya Pradesh Public Service Commission",
            "short": "MPPSC",
            "base_url": "https://www.mppsc.mp.gov.in",
            "pages": ["/"],
            "state": "Madhya Pradesh",
        },
        "rpsc": {
            "name": "Rajasthan Public Service Commission",
            "short": "RPSC",
            "base_url": "https://rpsc.rajasthan.gov.in",
            "pages": ["/"],
            "state": "Rajasthan",
        },
    }

    def __init__(self):
        super().__init__("state_psc", "https://uppsc.up.nic.in")

    def scrape(self):
        """Scrape all configured state PSCs."""
        all_results = []

        for state_key, config in self.STATES.items():
            self.logger.info(f"Scraping {config['short']}...")
            results = self._scrape_state(state_key, config)
            all_results.extend(results)

        return all_results

    def _scrape_state(self, state_key, config):
        """Scrape a single state PSC."""
        results = []

        for page_path in config["pages"]:
            url = f"{config['base_url']}{page_path}"
            try:
                html = self.fetch_html(url, timeout=15)
                if not html:
                    self.logger.warning(f"Could not fetch {url}")
                    continue

                soup = BeautifulSoup(html, "lxml")
                page_results = self._extract_notifications(soup, state_key, config)
                results.extend(page_results)
            except Exception as e:
                self.logger.warning(f"Error scraping {config['short']} {page_path}: {e}")

        return results

    def _extract_notifications(self, soup, state_key, config):
        """Extract notifications from a parsed HTML page."""
        results = []
        seen_titles = set()

        # Generic extraction: find all links that look like notifications
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
                    "recruitment", "advt", "advertisement", "notification",
                    "vacancy", "exam", "result", "admit", "answer key",
                    "application", "online form", "bharti", "भर्ती",
                    "परीक्षा", "niyukti", "selection", "interview",
                    "prelim", "mains", "syllabus",
                ]) or href.lower().endswith(".pdf")

                if not is_relevant:
                    continue

                seen_titles.add(title)
                link_url = make_absolute_url(config["base_url"], href)
                is_pdf = link_url and link_url.lower().endswith(".pdf")

                notification = {
                    "id": generate_id(state_key, title),
                    "title": title,
                    "organization": config["name"],
                    "organizationShort": config["short"],
                    "category": "state",
                    "subcategory": state_key,
                    "state": config["state"],
                    "notificationType": self._categorize(title),
                    "totalVacancies": self._extract_vacancies(title),
                    "qualifications": [],
                    "ageLimit": None,
                    "importantDates": {},
                    "applicationFee": None,
                    "links": {
                        "notification": link_url if is_pdf else None,
                        "detailPage": link_url if not is_pdf else None,
                        "officialWebsite": config["base_url"],
                    },
                    "source": config["base_url"].replace("https://", "").replace("http://", ""),
                    "sourceType": "html",
                    "confidence": 0.75,
                    "status": "active",
                }

                results.append(notification)
            except Exception as e:
                self.logger.debug(f"Error parsing {config['short']} link: {e}")

        return results

    def _categorize(self, title):
        """Categorize notification type."""
        t = title.lower()
        if any(kw in t for kw in ["result", "score", "merit", "cut off", "cutoff"]):
            return "result"
        elif any(kw in t for kw in ["admit card", "hall ticket", "e-admit"]):
            return "admit_card"
        elif any(kw in t for kw in ["answer key"]):
            return "answer_key"
        elif any(kw in t for kw in ["recruitment", "advt", "bharti", "vacancy", "notification"]):
            return "recruitment"
        elif any(kw in t for kw in ["syllabus", "pattern"]):
            return "syllabus"
        return "notification"

    def _extract_vacancies(self, title):
        """Extract vacancy count."""
        match = re.search(r"(\d+)\s*(?:posts?|vacancies|पद)", title, re.IGNORECASE)
        if match:
            count = int(match.group(1))
            if 1 <= count <= 100000:
                return count
        return None


# Standalone test
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    scraper = StatePSCScraper()
    result = scraper.run()
    print(f"\nStatus: {result['status']}, Items: {result['total_items']}, Time: {result['elapsed_seconds']}s")
    for item in result["items"][:15]:
        print(f"  📋 [{item['organizationShort']}] {item['title'][:90]}")
