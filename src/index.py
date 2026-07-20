"""
Main Entry Point — Orchestrates the full scraping pipeline.
=============================================================

Usage:
    python3 src/index.py                    # Run all scrapers
    python3 src/index.py --source ssc       # Run single scraper
    python3 src/index.py --source ssc,upsc  # Run specific scrapers

Pipeline:
    1. Run all scrapers (parallel-safe, sequential for now)
    2. Normalize all results to unified schema
    3. Deduplicate across sources
    4. Write output to data/jobs.json and data/meta.json
    5. Archive daily snapshot to data/archive/
"""

import sys
import os
import json
import logging
import argparse
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from scrapers.ssc import SSCScraper
from scrapers.upsc import UPSCScraper
from scrapers.ibps import IBPSScraper
from scrapers.state_psc import StatePSCScraper
from scrapers.railway import RailwayScraper
from scrapers.defence import DefenceScraper
from scrapers.employment_news import EmploymentNewsScraper
from normalizer import normalize_batch
from deduplicator import deduplicate


# Registry of all available scrapers
SCRAPERS = {
    "ssc": SSCScraper,
    "upsc": UPSCScraper,
    "ibps": IBPSScraper,
    "state_psc": StatePSCScraper,
    "railway": RailwayScraper,
    "defence": DefenceScraper,
    "employment_news": EmploymentNewsScraper,
}

# Output paths
DATA_DIR = PROJECT_ROOT / "data"
JOBS_FILE = DATA_DIR / "jobs.json"
META_FILE = DATA_DIR / "meta.json"
ARCHIVE_DIR = DATA_DIR / "archive"


def setup_logging():
    """Configure logging for the pipeline."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Suppress noisy urllib3 warnings
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def run_scrapers(sources=None):
    """
    Run specified scrapers (or all if sources is None).
    Returns combined results from all scrapers.
    """
    logger = logging.getLogger("pipeline")

    if sources:
        scraper_keys = [s.strip() for s in sources if s.strip() in SCRAPERS]
    else:
        scraper_keys = list(SCRAPERS.keys())

    logger.info(f"Running {len(scraper_keys)} scrapers: {', '.join(scraper_keys)}")

    all_items = []
    source_status = {}

    for key in scraper_keys:
        scraper_class = SCRAPERS[key]
        scraper = scraper_class()
        result = scraper.run()

        source_status[key] = {
            "status": result["status"],
            "items": result["total_items"],
            "elapsed": result["elapsed_seconds"],
            "error": result.get("error"),
        }

        if result["status"] == "success":
            all_items.extend(result["items"])
        else:
            logger.warning(f"Scraper {key} failed: {result.get('error', 'unknown')}")

    # AI PDF Extraction Phase (if GEMINI_API_KEY is available)
    try:
        from pdf_parser import parse_pdf_with_ai
        import os, re as _re
        if os.environ.get("GEMINI_API_KEY"):
            logger.info("🤖 Starting AI PDF Extraction Phase...")
            
            def find_pdf_in_page(page_url):
                """Visit an HTML detail page and find the first .pdf link on it."""
                try:
                    import requests as _requests
                    from urllib.parse import urljoin
                    headers = {"User-Agent": "Mozilla/5.0 (compatible; GovJobBot/1.0)"}
                    resp = _requests.get(page_url, headers=headers, timeout=20, verify=False)
                    resp.raise_for_status()
                    html = resp.text
                    # Find all href attributes that contain .pdf
                    pdf_links = _re.findall(r'href=["\']([^"\']+\.pdf(?:\?[^"\']*)?)["\']', html, _re.IGNORECASE)
                    if not pdf_links:
                        return None
                    return urljoin(page_url, pdf_links[0])
                except Exception as e:
                    logger.warning(f"Could not crawl detailPage {page_url}: {e}")
                    return None

            for job in all_items:
                # Skip if already fully enriched (has applicationFee set from a previous run)
                if job.get('applicationFee') is not None and job.get('documentCategory'):
                    continue
                
                links = job.get('links', {})
                pdf_url = links.get('notification')
                
                # Case 1: We have a direct PDF link
                if pdf_url and pdf_url.lower().endswith('.pdf'):
                    pass  # use it as-is
                
                # Case 2: No PDF — try to discover one from the detail page
                elif not pdf_url or not pdf_url.lower().endswith('.pdf'):
                    detail_page = links.get('detailPage') or links.get('officialWebsite')
                    if detail_page:
                        logger.info(f"🔍 No PDF link found, crawling detailPage: {detail_page[:60]}...")
                        discovered = find_pdf_in_page(detail_page)
                        if discovered:
                            logger.info(f"   ✅ Discovered PDF: {discovered[:60]}...")
                            job['links']['notification'] = discovered
                            pdf_url = discovered
                        else:
                            logger.info(f"   ⚠️  No PDF found on detailPage. Skipping AI enrichment.")
                            continue
                    else:
                        continue  # No links at all, skip

                if pdf_url and pdf_url.lower().endswith('.pdf'):
                    logger.info(f"Extracting rich data from PDF: {job['title'][:40]}...")
                    enriched_data = parse_pdf_with_ai(pdf_url)
                    if enriched_data:
                        fields_to_merge = [
                            'documentCategory', 'categorySubtitle', 
                            'applicationFee', 'applicationFeeDetails', 'feeNote',
                            'ageLimit', 'ageLimitDetails',
                            'totalVacancies', 'vacancyBreakdown',
                            'importantDates', 'eligibilitySummary', 
                            'eligibilityDetails', 'selectionProcess', 'payScale'
                        ]
                        for field in fields_to_merge:
                            if enriched_data.get(field):
                                if isinstance(enriched_data[field], dict) and isinstance(job.get(field), dict):
                                    job[field].update(enriched_data[field])
                                else:
                                    job[field] = enriched_data[field]
                        
                        logger.info(f"✅ Successfully enriched: {job['title'][:40]}")
    except ImportError:
        logger.warning("pdf_parser module not found or missing dependencies.")

    return all_items, source_status


def process_items(raw_items):
    """Normalize and deduplicate the raw scraped items."""
    logger = logging.getLogger("pipeline")

    # Step 1: Normalize
    normalized, skipped = normalize_batch(raw_items)
    logger.info(f"Normalized: {len(normalized)} items ({skipped} skipped)")

    # Step 2: Deduplicate
    deduplicated, dup_count = deduplicate(normalized)
    logger.info(f"Deduplicated: {len(deduplicated)} items ({dup_count} duplicates removed)")

    return deduplicated


def load_existing_jobs():
    """Load the existing jobs.json to merge with new data."""
    if JOBS_FILE.exists():
        try:
            with open(JOBS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def merge_with_existing(new_items, existing_items):
    """
    Merge new scraped items with existing data.
    New items override existing ones with the same ID.
    """
    # Build lookup of existing items by ID
    existing_lookup = {item["id"]: item for item in existing_items}

    # Override/add new items
    for item in new_items:
        existing_lookup[item["id"]] = item

    return list(existing_lookup.values())


def write_output(items, source_status):
    """Write the final output to data/ directory."""
    logger = logging.getLogger("pipeline")

    # Create directories
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    # Sort items: active first, then by notification date (newest first)
    items.sort(
        key=lambda x: (
            0 if x.get("status") == "active" else 1,
            x.get("importantDates", {}).get("notificationDate") or "0000",
        ),
        reverse=False,
    )
    # Reverse so newest first
    active = [i for i in items if i.get("status") == "active"]
    expired = [i for i in items if i.get("status") != "active"]
    items = active + expired

    # Write jobs.json
    with open(JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    logger.info(f"Written {len(items)} items to {JOBS_FILE}")

    # Write meta.json
    now = datetime.now(timezone.utc)
    meta = {
        "lastScrapeAt": now.isoformat(),
        "lastScrapeDate": now.strftime("%Y-%m-%d"),
        "totalJobs": len(items),
        "activeJobs": len(active),
        "expiredJobs": len(expired),
        "sources": source_status,
        "categories": _count_by_field(items, "category"),
        "notificationTypes": _count_by_field(items, "notificationType"),
        "organizations": _count_by_field(items, "organizationShort"),
    }

    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    logger.info(f"Written metadata to {META_FILE}")

    # Write daily archive
    archive_file = ARCHIVE_DIR / f"{now.strftime('%Y-%m-%d')}.json"
    with open(archive_file, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    logger.info(f"Archived to {archive_file}")

    return meta


def _count_by_field(items, field):
    """Count items grouped by a field value."""
    counts = {}
    for item in items:
        val = item.get(field, "unknown")
        counts[val] = counts.get(val, 0) + 1
    return counts


def main():
    """Main pipeline execution."""
    parser = argparse.ArgumentParser(description="Sarkari Job Notification Scraper")
    parser.add_argument(
        "--source", "-s",
        help="Comma-separated list of sources to scrape (default: all)",
        default=None,
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Start fresh (don't merge with existing data)",
    )
    args = parser.parse_args()

    setup_logging()
    logger = logging.getLogger("pipeline")

    logger.info("=" * 60)
    logger.info("🚀 Starting Sarkari Job Notification Scraper Pipeline")
    logger.info("=" * 60)

    # Parse sources
    sources = args.source.split(",") if args.source else None

    # Step 1: Run scrapers
    raw_items, source_status = run_scrapers(sources)
    logger.info(f"Total raw items collected: {len(raw_items)}")

    # Step 2: Normalize + deduplicate
    processed_items = process_items(raw_items)

    # Step 3: Merge with existing data (unless --fresh)
    if not args.fresh:
        existing = load_existing_jobs()
        if existing:
            logger.info(f"Merging with {len(existing)} existing items")
            processed_items = merge_with_existing(processed_items, existing)
            # Re-deduplicate after merge
            processed_items, _ = deduplicate(processed_items)

    # Step 4: Write output
    meta = write_output(processed_items, source_status)

    # Print summary
    logger.info("=" * 60)
    logger.info("✅ Pipeline Complete!")
    logger.info(f"   Total jobs: {meta['totalJobs']}")
    logger.info(f"   Active: {meta['activeJobs']}")
    logger.info(f"   Sources: {len(source_status)}")
    logger.info("=" * 60)

    # Print source summary
    for source, status in source_status.items():
        icon = "✅" if status["status"] == "success" else "❌"
        logger.info(f"   {icon} {source}: {status['items']} items ({status['elapsed']}s)")

    print(f"\nOutput: {JOBS_FILE}")
    print(f"Meta:   {META_FILE}")


if __name__ == "__main__":
    main()
