"""
UPSC (Union Public Service Commission) Scraper
================================================
UPSC runs a server-rendered Drupal site at upsc.gov.in.
We parse the HTML to extract notifications, exam results, and admit cards.
No headless browser needed — standard HTTP fetch works.
"""

import sys
import os
import json
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from base import BaseScraper, generate_id, parse_date, clean_text, make_absolute_url

from bs4 import BeautifulSoup


class UPSCScraper(BaseScraper):
    """Scrapes upsc.gov.in for recruitment notifications, results, and admit cards."""

    BASE = "https://www.upsc.gov.in"

    # Key pages to scrape
    PAGES = {
        "home": "/",
        "active_exams": "/active-examinations-recruitments",
        "whats_new": "/whats-new",
    }

    def __init__(self):
        super().__init__("upsc", self.BASE)

    def scrape(self):
        results = []

        # 1. Scrape "What's New" section (latest notifications)
        whats_new = self._scrape_whats_new()
        results.extend(whats_new)

        # 2. Scrape active examinations/recruitments
        active = self._scrape_active_exams()
        results.extend(active)

        # 3. Scrape homepage marquee/ticker for breaking updates
        homepage = self._scrape_homepage()
        results.extend(homepage)

        return results

    def _scrape_whats_new(self):
        """Parse the 'What's New' page for latest notifications."""
        url = f"{self.BASE}{self.PAGES['whats_new']}"
        html = self.fetch_html(url)
        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        results = []

        # UPSC lists notifications in tables or div-based lists
        # Look for common patterns: tables, view content divs
        rows = soup.select("table tbody tr")
        if not rows:
            rows = soup.select(".view-content .views-row")

        for row in rows:
            try:
                notification = self._parse_whats_new_row(row)
                if notification:
                    results.append(notification)
            except Exception as e:
                self.logger.debug(f"Error parsing UPSC what's new row: {e}")
                continue

        return results

    def _parse_whats_new_row(self, row):
        """Parse a single row from the What's New listing."""
        # Try table row format
        cells = row.select("td")
        if cells and len(cells) >= 2:
            date_cell = cells[0]
            content_cell = cells[1] if len(cells) > 1 else cells[0]

            date_text = clean_text(date_cell.get_text())
            pub_date = parse_date(date_text)

            # Get the title and link
            link = content_cell.select_one("a")
            if link:
                title = clean_text(link.get_text())
                href = link.get("href", "")
                link_url = make_absolute_url(self.BASE, href)
            else:
                title = clean_text(content_cell.get_text())
                link_url = None
        else:
            # div-based format
            link = row.select_one("a")
            if link:
                title = clean_text(link.get_text())
                href = link.get("href", "")
                link_url = make_absolute_url(self.BASE, href)
            else:
                title = clean_text(row.get_text())
                link_url = None
            pub_date = None

        if not title or len(title) < 5:
            return None

        # Categorize the notification
        notification_type = self._categorize_notification(title)

        # Check if link points to a PDF
        is_pdf = link_url and link_url.lower().endswith(".pdf")

        notification = {
            "id": generate_id("upsc", title),
            "title": title,
            "organization": "Union Public Service Commission (UPSC)",
            "organizationShort": "UPSC",
            "category": "central",
            "subcategory": "upsc",
            "notificationType": notification_type,
            "totalVacancies": self._extract_vacancy_count(title),
            "qualifications": [],
            "ageLimit": None,
            "importantDates": {
                "notificationDate": pub_date,
            },
            "applicationFee": None,
            "links": {
                "applyOnline": f"{self.BASE}/apply" if notification_type == "recruitment" else None,
                "notification": link_url if is_pdf else None,
                "detailPage": link_url if not is_pdf else None,
                "officialWebsite": self.BASE,
            },
            "source": "upsc.gov.in",
            "sourceType": "html",
            "confidence": 0.85,
            "status": "active",
        }

        return notification

    def _scrape_active_exams(self):
        """Parse the active examinations page."""
        url = f"{self.BASE}{self.PAGES['active_exams']}"
        html = self.fetch_html(url)
        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        results = []

        # Look for exam listings — typically in tables or structured divs
        rows = soup.select("table tbody tr")
        if not rows:
            rows = soup.select(".view-content .views-row, .field-content a")

        for row in rows:
            try:
                link = row if row.name == "a" else row.select_one("a")
                if not link:
                    continue

                title = clean_text(link.get_text())
                href = link.get("href", "")
                if not title or len(title) < 5:
                    continue

                link_url = make_absolute_url(self.BASE, href)

                notification = {
                    "id": generate_id("upsc", title),
                    "title": title,
                    "organization": "Union Public Service Commission (UPSC)",
                    "organizationShort": "UPSC",
                    "category": "central",
                    "subcategory": "upsc",
                    "notificationType": self._categorize_notification(title),
                    "totalVacancies": self._extract_vacancy_count(title),
                    "qualifications": [],
                    "ageLimit": None,
                    "importantDates": {},
                    "applicationFee": None,
                    "links": {
                        "detailPage": link_url,
                        "officialWebsite": self.BASE,
                    },
                    "source": "upsc.gov.in",
                    "sourceType": "html",
                    "confidence": 0.80,
                    "status": "active",
                }

                results.append(notification)
            except Exception as e:
                self.logger.debug(f"Error parsing UPSC active exam row: {e}")
                continue

        return results

    def _scrape_homepage(self):
        """Scrape the homepage for marquee/scrolling ticker notifications."""
        url = self.BASE
        html = self.fetch_html(url)
        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        results = []

        # Look for marquee/ticker elements and important notice sections
        tickers = soup.select("marquee a, .ticker a, .scroll-text a, .imp-notice a, .whatsnew a")

        seen_titles = set()
        for link in tickers:
            try:
                title = clean_text(link.get_text())
                if not title or len(title) < 10 or title in seen_titles:
                    continue
                seen_titles.add(title)

                href = link.get("href", "")
                link_url = make_absolute_url(self.BASE, href)
                is_pdf = link_url and link_url.lower().endswith(".pdf")

                notification = {
                    "id": generate_id("upsc", title),
                    "title": title,
                    "organization": "Union Public Service Commission (UPSC)",
                    "organizationShort": "UPSC",
                    "category": "central",
                    "subcategory": "upsc",
                    "notificationType": self._categorize_notification(title),
                    "totalVacancies": self._extract_vacancy_count(title),
                    "qualifications": [],
                    "ageLimit": None,
                    "importantDates": {},
                    "applicationFee": None,
                    "links": {
                        "notification": link_url if is_pdf else None,
                        "detailPage": link_url if not is_pdf else None,
                        "officialWebsite": self.BASE,
                    },
                    "source": "upsc.gov.in",
                    "sourceType": "html",
                    "confidence": 0.80,
                    "status": "active",
                }

                results.append(notification)
            except Exception as e:
                self.logger.debug(f"Error parsing UPSC ticker: {e}")
                continue

        return results

    def _categorize_notification(self, title):
        """Categorize a notification based on its title keywords."""
        title_lower = title.lower()
        if any(kw in title_lower for kw in ["result", "mark", "score"]):
            return "result"
        elif any(kw in title_lower for kw in ["admit card", "e-admit", "hall ticket"]):
            return "admit_card"
        elif any(kw in title_lower for kw in ["answer key", "answerkey"]):
            return "answer_key"
        elif any(kw in title_lower for kw in [
            "recruitment", "vacancy", "advt", "advertisement",
            "notification", "online form", "application", "invites"
        ]):
            return "recruitment"
        elif any(kw in title_lower for kw in ["syllabus", "exam pattern"]):
            return "syllabus"
        elif any(kw in title_lower for kw in ["corrigendum", "addendum", "errata", "extension"]):
            return "corrigendum"
        return "notification"

    def _extract_vacancy_count(self, title):
        """Try to extract vacancy/post count from the title."""
        patterns = [
            r"(\d+)\s*(?:posts?|vacancies|vacanc)",
            r"for\s+(\d+)\s+",
            r"(\d+)\s+(?:nos?\.?|number)",
        ]
        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                count = int(match.group(1))
                if 1 <= count <= 100000:  # Sanity check
                    return count
        return None


# Allow running standalone
if __name__ == "__main__":
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    scraper = UPSCScraper()
    result = scraper.run()

    print(f"\nStatus: {result['status']}")
    print(f"Items found: {result['total_items']}")
    print(f"Time: {result['elapsed_seconds']}s")

    for item in result["items"][:10]:
        print(f"\n  📋 {item['title'][:100]}")
        print(f"     Type: {item.get('notificationType', '?')}")
        link = item.get("links", {}).get("detailPage") or item.get("links", {}).get("notification")
        if link:
            print(f"     Link: {link[:100]}")

    if result["total_items"] > 10:
        print(f"\n  ... and {result['total_items'] - 10} more items")
