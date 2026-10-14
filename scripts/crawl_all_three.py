"""Run all three scrapers (CareerViet, ITviec, TopCV) and write to unified CSV.

Pulls raw job descriptions and candidate requirements from all 3 sources.
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

from job_scraper.scrapers.careerviet import CareerVietScraper
from job_scraper.scrapers.itviec import ITViecScraper
from job_scraper.scrapers.topcv import TopCVScraper
from job_scraper.storage.csv_writer import write_records

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("crawl_all")


def run_all(output: str = "data/jobs.csv") -> None:
    target = Path(output)
    total_added = 0
    total_skipped = 0
    start = time.time()

    # 1. CAREERVIET (Marketing & CNTT)
    log.info("=== [1/3] BẮT ĐẦU CÀO CAREERVIET ===")
    cv_scraper = CareerVietScraper()
    try:
        cv_tasks = [
            ("marketing", 2),
            ("digital marketing", 1),
            ("lap trinh", 2),
            ("data analyst", 1),
        ]
        for kw, pages in cv_tasks:
            log.info("CareerViet: kw='%s', pages=%d", kw, pages)
            recs = cv_scraper.scrape(kw, pages=pages, fast=False)
            add, skip = write_records(target, recs)
            total_added += add
            total_skipped += skip
            log.info("  -> Added %d, Skipped %d", add, skip)
    finally:
        cv_scraper.close()

    # 2. ITVIEC (CNTT & Data)
    log.info("=== [2/3] BẮT ĐẦU CÀO ITVIEC ===")
    it_scraper = ITViecScraper()
    try:
        it_tasks = [
            ("python", 1),
            ("react", 1),
            ("ai", 1),
            ("product manager", 1),
        ]
        for kw, pages in it_tasks:
            log.info("ITviec: kw='%s', pages=%d", kw, pages)
            recs = it_scraper.scrape(kw, pages=pages, fast=False)
            add, skip = write_records(target, recs)
            total_added += add
            total_skipped += skip
            log.info("  -> Added %d, Skipped %d", add, skip)
    finally:
        it_scraper.close()

    # 3. TOPCV (Bypass Playwright, Marketing & CNTT)
    log.info("=== [3/3] BẮT ĐẦU CÀO TOPCV ===")
    topcv_scraper = TopCVScraper()
    try:
        topcv_tasks = [
            ("marketing", 1),
            ("developer", 1),
        ]
        for kw, pages in topcv_tasks:
            log.info("TopCV: kw='%s', pages=%d", kw, pages)
            recs = topcv_scraper.scrape(kw, pages=pages, fast=False)
            add, skip = write_records(target, recs)
            total_added += add
            total_skipped += skip
            log.info("  -> Added %d, Skipped %d", add, skip)
    finally:
        topcv_scraper.close()

    elapsed = time.time() - start
    log.info("HOÀN THÀNH CẢ 3 NGUỒN trong %.1fs: %d jobs mới, %d jobs trùng -> %s", elapsed, total_added, total_skipped, target)


if __name__ == "__main__":
    out_file = sys.argv[1] if len(sys.argv) > 1 else "data/jobs.csv"
    run_all(out_file)
