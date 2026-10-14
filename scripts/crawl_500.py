"""Batch crawler to collect > 500 job postings across industries.

Prioritizes IT and Marketing, also gathers Sales, Design, Finance, HR.
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

from job_scraper.scrapers.careerviet import CareerVietScraper
from job_scraper.scrapers.itviec import ITViecScraper
from job_scraper.storage.csv_writer import write_records

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("crawl_500")

# Plan: Target > 500 unique jobs
TASKS: list[tuple[str, str, int]] = [
    # (source, keyword, pages)
    # --- MARKETING (CareerViet: ~50 jobs/page) ---
    ("careerviet", "marketing", 3),             # ~150
    ("careerviet", "digital marketing", 2),     # ~100
    ("careerviet", "content", 2),               # ~100
    ("careerviet", "seo", 1),                   # ~50
    ("careerviet", "brand", 1),                 # ~50

    # --- CNTT / IT (ITviec: ~20/page, CareerViet: ~50/page) ---
    ("itviec", "python", 2),                    # ~40
    ("itviec", "java", 2),                      # ~40
    ("itviec", "react", 2),                     # ~40
    ("itviec", "golang", 2),                    # ~40
    ("itviec", "data", 2),                      # ~40
    ("itviec", "devops", 2),                    # ~40
    ("itviec", "tester", 2),                    # ~40
    ("careerviet", "lap trinh", 2),             # ~100
    ("careerviet", "data analyst", 1),          # ~50

    # --- OTHER INDUSTRIES ---
    ("careerviet", "sales", 2),                 # ~100
    ("careerviet", "thiet ke do hoa", 1),       # ~50
    ("careerviet", "nhan su", 1),               # ~50
    ("careerviet", "ke toan", 1),               # ~50
]


def run(output_path: str = "data/jobs.csv") -> int:
    target = Path(output_path)
    total_added = 0
    total_skipped = 0

    scrapers = {
        "careerviet": CareerVietScraper(timeout=20.0),
        "itviec": ITViecScraper(timeout=20.0),
    }

    log.info("Starting batch crawl targeting > 500 jobs -> %s", target)
    start_time = time.time()

    for idx, (source, keyword, pages) in enumerate(TASKS, 1):
        scraper = scrapers.get(source)
        if not scraper:
            continue
        log.info("[%d/%d] Scraping %s: keyword='%s', pages=%d", idx, len(TASKS), source, keyword, pages)
        try:
            records = scraper.scrape(keyword=keyword, pages=pages, fast=True)
            if records:
                added, skipped = write_records(target, records)
                total_added += added
                total_skipped += skipped
                log.info("  -> Added %d new, %d duplicates (total new this run: %d)", added, skipped, total_added)
            else:
                log.warning("  -> No records found")
        except Exception as exc:
            log.error("  -> Error scraping %s '%s': %s", source, keyword, exc)
        time.sleep(1.0)  # gentle rate limit

    elapsed = time.time() - start_time
    log.info("Batch crawl finished in %.1fs: %d new jobs added, %d duplicates skipped.", elapsed, total_added, total_skipped)
    return total_added


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "data/jobs.csv"
    run(out)
