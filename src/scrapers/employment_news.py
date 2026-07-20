"""
Employment News / Rozgar Samachar Scraper
==========================================
Employment News is the official weekly gazette for government job 
advertisements published by the Ministry of Information & Broadcasting.
"""

import sys
import os
import json
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from base import BaseScraper, generate_id, parse_date, clean_text, make_absolute_url

from bs4 import BeautifulSoup


class EmploymentNewsScraper(BaseScraper):
    """Scrapes employmentnews.gov.in for weekly job gazette notifications."""

    BASE = "https://www.employmentnews.gov.in"

    def __init__(self):
        super().__init__("employment_news", self.BASE)

    def scrape(self):
        results = []

        # Try RSS feed first (faster and more structured)
        rss_results = self._scrape_rss()
        results.extend(rss_results)

        # Fallback to HTML parsing if RSS doesn't yield results
        if not results:
            html_results = self._scrape_html()
            results.extend(html_results)

        return results

    def _scrape_rss(self):
        """Try to parse the Employment News RSS feed."""
        rss_url = f"{self.BASE}/RSS.aspx"
        html = self.fetch_html(rss_url, timeout=15)
        if not html:
            return []

        try:
            soup = BeautifulSoup(html, "lxml-xml")
            items = soup.select("item")
            results = []

            for item in items:
                try:
                    title = clean_text(item.select_one("title").get_text()) if item.select_one("title") else ""
                    link = item.select_one("link").get_text().strip() if item.select_one("link") else ""
                    pub_date = item.select_one("pubDate").get_text().strip() if item.select_one("pubDate") else ""
                    description = clean_text(item.select_one("description").get_text()) if item.select_one("description") else ""

                    if not title or len(title) < 5:
                        continue

                    notification = {
                        "id": generate_id("employment_news", title),
                        "title": title,
                        "organization": "Employment News (Govt of India)",
                        "organizationShort": "EmpNews",
                        "category": "central",
                        "subcategory": "employment_news",
                        "notificationType": "recruitment",
                        "description": description,
                        "totalVacancies": None,
                        "qualifications": [],
                        "ageLimit": None,
                        "importantDates": {
                            "publishDate": parse_date(pub_date),
                        },
                        "applicationFee": None,
                        "links": {
                            "detailPage": link,
                            "officialWebsite": self.BASE,
                        },
                        "source": "employmentnews.gov.in",
                        "sourceType": "rss",
                        "confidence": 0.85,
                        "status": "active",
                    }
                    results.append(notification)
                except Exception as e:
                    self.logger.debug(f"Error parsing RSS item: {e}")

            return results
        except Exception:
            return []

    def _scrape_html(self):
        """Fallback: scrape the homepage HTML."""
        html = self.fetch_html(self.BASE, timeout=15)
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
                    "recruitment", "vacancy", "notification", "advt",
                    "employment", "job", "post", "bharti",
                ])

                if not is_relevant:
                    continue

                seen_titles.add(title)
                link_url = make_absolute_url(self.BASE, href)

                notification = {
                    "id": generate_id("employment_news", title),
                    "title": title,
                    "organization": "Employment News (Govt of India)",
                    "organizationShort": "EmpNews",
                    "category": "central",
                    "subcategory": "employment_news",
                    "notificationType": "recruitment",
                    "totalVacancies": None,
                    "qualifications": [],
                    "ageLimit": None,
                    "importantDates": {},
                    "applicationFee": None,
                    "links": {
                        "detailPage": link_url,
                        "officialWebsite": self.BASE,
                    },
                    "source": "employmentnews.gov.in",
                    "sourceType": "html",
                    "confidence": 0.75,
                    "status": "active",
                }
                results.append(notification)
            except Exception as e:
                self.logger.debug(f"Error parsing EmpNews link: {e}")

        return results


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    scraper = EmploymentNewsScraper()
    result = scraper.run()
    print(f"\nStatus: {result['status']}, Items: {result['total_items']}, Time: {result['elapsed_seconds']}s")
    for item in result["items"][:10]:
        print(f"  📋 {item['title'][:100]}")
