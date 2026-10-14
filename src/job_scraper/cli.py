"""Command line interface."""

from __future__ import annotations

import argparse
import logging
import sys

from job_scraper.scrapers.careerviet import CareerVietScraper
from job_scraper.scrapers.generic import GenericScraper
from job_scraper.scrapers.itviec import ITViecScraper
from job_scraper.scrapers.topcv import TopCVScraper
from job_scraper.storage.csv_writer import write_records

SOURCES = {
    "topcv": TopCVScraper,
    "itviec": ITViecScraper,
    "careerviet": CareerVietScraper,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="job_scraper",
        description="Scrape job postings from TopCV, ITviec, CareerViet, or any URL into one CSV.",
    )
    parser.add_argument("--source", required=True, choices=["topcv", "itviec", "careerviet", "generic"],
                        help="topcv | itviec | careerviet | generic")
    parser.add_argument("--keyword", default="", help="search keyword (topcv, itviec)")
    parser.add_argument("--pages", type=int, default=1, help="number of listing pages (default 1)")
    parser.add_argument("--url", default="", help="page URL, required when --source generic")
    parser.add_argument("-o", "--output", default="data/jobs.csv", help="output CSV path")
    parser.add_argument("--fast", action="store_true",
                        help="skip detail pages (listing data only)")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )
    if args.pages < 1:
        print("error: --pages must be >= 1", file=sys.stderr)
        return 2
    if args.source == "generic":
        if not args.url:
            print("error: --url is required when --source generic", file=sys.stderr)
            return 2
        scraper = GenericScraper(args.url)
    else:
        scraper = SOURCES[args.source]()

    records = scraper.scrape(keyword=args.keyword, pages=args.pages, fast=args.fast)
    if not records:
        print("no jobs found")
        return 0
    added, skipped = write_records(args.output, records)
    print(f"done: {added} added, {skipped} duplicates skipped -> {args.output}")
    return 0
