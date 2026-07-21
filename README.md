# GetSarkariResult.net Scraper Pipeline

This repository contains the automated web scraping and static site generation pipeline for [getsarkariresult.net](https://getsarkariresult.net).

## Overview

The pipeline runs entirely via GitHub Actions. It automates the process of checking Indian Government websites for new job notifications, admit cards, and results.

1. **Scraping (`src/scrapers/`)**: Custom Python scrapers fetch data from official sources (UPSC, SSC, RRB, etc.). Most scrapers rely on BeautifulSoup and requests. (Note: SSC scraping leverages a hidden JSON API instead of browser automation, making it resilient to bot blocks).
2. **AI Enrichment (`src/ai_enrichment.py`)**: For complex PDF notifications, the pipeline uses Google's Gemini AI API to extract structured fields like vacancies, age limits, and fees.
3. **Data Normalization (`src/normalizer.py` / `src/deduplicator.py`)**: Data is cleansed and deduped against historical records stored in `data/jobs.json`.
4. **Static Site Generation (`src/build_html.py`)**: Pure HTML pages are rebuilt from the latest JSON data.
5. **Deployment**: Changes are committed back to the repository and instantly deployed via Cloudflare Pages.

## Automation

The GitHub Action (`.github/workflows/scrape.yml`) runs on a scheduled cron job every 60 minutes. It handles the complete end-to-end process from scraping to deployment without manual intervention.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
