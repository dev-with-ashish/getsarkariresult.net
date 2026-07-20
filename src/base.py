"""
Base scraper class and shared utilities for the govt job notification pipeline.
All scrapers inherit from BaseScraper and implement the scrape() method.
"""

import requests
import hashlib
import logging
import time
import re
from datetime import datetime, timezone
from abc import ABC, abstractmethod

# Standard headers to mimic a real browser
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
}

JSON_HEADERS = {
    **DEFAULT_HEADERS,
    "Accept": "application/json, text/plain, */*",
}

logger = logging.getLogger("scraper")


class BaseScraper(ABC):
    """
    Abstract base class for all government job notification scrapers.
    Each scraper targets a specific source (SSC, UPSC, IBPS, etc.)
    and implements the scrape() method to return normalized job data.
    """

    def __init__(self, name, base_url):
        self.name = name
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.logger = logging.getLogger(f"scraper.{name}")

    @abstractmethod
    def scrape(self):
        """
        Scrape the source and return a list of normalized job notification dicts.
        Each dict should follow the unified schema (see normalizer.py).
        Returns: list[dict]
        """
        pass

    def fetch_html(self, url, timeout=30, retries=3):
        """Fetch HTML content with retries and error handling."""
        for attempt in range(retries):
            try:
                # Many govt sites have expired or invalid SSL certs, so verify=False is required
                resp = self.session.get(url, timeout=timeout, verify=False)
                resp.raise_for_status()
                return resp.text
            except requests.RequestException as e:
                self.logger.warning(
                    f"Attempt {attempt + 1}/{retries} failed for {url}: {e}"
                )
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
        self.logger.error(f"All {retries} attempts failed for {url}")
        return None

    def fetch_json(self, url, timeout=30, retries=3):
        """Fetch JSON data from an API endpoint with retries."""
        for attempt in range(retries):
            try:
                resp = self.session.get(
                    url, timeout=timeout, headers=JSON_HEADERS, verify=False
                )
                resp.raise_for_status()
                return resp.json()
            except (requests.RequestException, ValueError) as e:
                self.logger.warning(
                    f"Attempt {attempt + 1}/{retries} failed for {url}: {e}"
                )
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
        self.logger.error(f"All {retries} attempts failed for {url}")
        return None

    def run(self):
        """Execute the scraper with timing and error handling."""
        self.logger.info(f"Starting scraper: {self.name}")
        start = time.time()
        try:
            results = self.scrape()
            elapsed = time.time() - start
            self.logger.info(
                f"Scraper {self.name} finished: {len(results)} items in {elapsed:.1f}s"
            )
            return {
                "source": self.name,
                "base_url": self.base_url,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "elapsed_seconds": round(elapsed, 1),
                "total_items": len(results),
                "status": "success",
                "items": results,
            }
        except Exception as e:
            elapsed = time.time() - start
            self.logger.error(f"Scraper {self.name} failed after {elapsed:.1f}s: {e}")
            return {
                "source": self.name,
                "base_url": self.base_url,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "elapsed_seconds": round(elapsed, 1),
                "total_items": 0,
                "status": "error",
                "error": str(e),
                "items": [],
            }


def generate_id(source, title):
    """Generate a deterministic unique ID from source + title."""
    raw = f"{source}:{title}".lower().strip()
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def clean_text(text):
    """Clean whitespace, newlines, and HTML artifacts from text."""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[\r\n\t]+", " ", text)
    return text.strip()


def parse_date(date_str):
    """
    Try to parse various date formats commonly found on govt websites.
    Returns ISO format string or None.
    """
    if not date_str:
        return None

    date_str = clean_text(date_str)

    # Common Indian govt date formats
    formats = [
        "%d/%m/%Y",      # 15/07/2026
        "%d-%m-%Y",      # 15-07-2026
        "%d.%m.%Y",      # 15.07.2026
        "%Y-%m-%d",      # 2026-07-15 (ISO)
        "%Y-%m-%dT%H:%M:%S",  # 2026-07-15T10:30:00
        "%Y-%m-%dT%H:%M:%S.%fZ",  # 2026-07-15T10:30:00.000Z
        "%d %B %Y",      # 15 July 2026
        "%d %b %Y",      # 15 Jul 2026
        "%d %B, %Y",     # 15 July, 2026
        "%d %b, %Y",     # 15 Jul, 2026
        "%B %d, %Y",     # July 15, 2026
        "%b %d, %Y",     # Jul 15, 2026
        "%d-%b-%Y",      # 15-Jul-2026
        "%d/%b/%Y",      # 15/Jul/2026
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Handle ISO with timezone offset like 2026-07-15T10:30:00.000Z
    try:
        if "T" in date_str:
            # Strip timezone suffix for simple parsing
            clean = date_str.split("T")[0]
            dt = datetime.strptime(clean, "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d")
    except ValueError:
        pass

    return None


def make_absolute_url(base_url, path):
    """Convert a relative path to absolute URL."""
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if path.startswith("//"):
        return "https:" + path
    if path.startswith("/"):
        # Extract scheme + domain from base_url
        from urllib.parse import urlparse
        parsed = urlparse(base_url)
        return f"{parsed.scheme}://{parsed.netloc}{path}"
    return base_url.rstrip("/") + "/" + path.lstrip("/")
