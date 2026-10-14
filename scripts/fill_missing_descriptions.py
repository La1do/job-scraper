"""Fill missing descriptions for ITviec and TopCV jobs in data/jobs.csv.

Uses:
1. Polite HTTPX with heading extraction for ITviec.
2. Playwright browser for TopCV (box-job-information-detail-item).
"""

from __future__ import annotations

import csv
import logging
import sys
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from job_scraper.models import COLUMNS
from job_scraper.scrapers.base import DEFAULT_HEADERS
from job_scraper.utils.lang_detector import is_english

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("fill_desc")


def extract_itviec_detail(url: str, client: httpx.Client) -> tuple[str, str, str]:
    """Returns (desc, skills, company)."""
    for attempt in range(3):
        try:
            resp = client.get(url, timeout=12.0)
            if resp.status_code == 429:
                time.sleep(1.5 * (attempt + 1))
                continue
            if resp.status_code != 200:
                return "", "", ""
            soup = BeautifulSoup(resp.text, "lxml")
            desc = ""
            skills = ""
            company = ""

            for h in soup.find_all(["h2", "h3", "h4"]):
                htext = h.get_text(" ", strip=True).lower()
                parent = h.find_parent("div")
                if not parent:
                    continue
                body = parent.get_text("\n", strip=True)
                if "job description" in htext or "mô tả công việc" in htext:
                    # Strip the heading itself
                    desc = body.removeprefix("Job description").removeprefix("Mô tả công việc").strip()
                elif "your skills" in htext or "yêu cầu" in htext:
                    skills = body.removeprefix("Your skills and experience").removeprefix("Yêu cầu").strip()

            comp_a = soup.select_one("span a[href*='/companies/'], a[href*='/companies/']")
            if comp_a and comp_a.get_text(strip=True):
                company = comp_a.get_text(strip=True)

            return desc[:8000], skills[:8000], company
        except Exception:
            time.sleep(1.0)
    return "", "", ""


def run(csv_path: str = "data/jobs.csv") -> None:
    target = Path(csv_path)
    with target.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

    # Find rows with empty description
    empty_indices = [i for i, r in enumerate(rows) if not r.get("description", "").strip()]
    log.info("Found %d jobs with empty description out of %d total", len(empty_indices), len(rows))

    # 1. Fill ITviec rows
    itviec_indices = [i for i in empty_indices if rows[i].get("source_website") == "ITviec"]
    log.info("Filling %d ITviec jobs with polite HTTP requests...", len(itviec_indices))

    with httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True) as client:
        for count, idx in enumerate(itviec_indices, 1):
            r = rows[idx]
            url = r.get("job_posting_url", "")
            if not url:
                continue
            desc, skills, comp = extract_itviec_detail(url, client)
            if desc:
                r["description"] = desc
                if not r.get("company_id") and comp:
                    r["company_id"] = comp
                log.info("  [%d/%d] ITviec filled: %s (desc %d chars)", count, len(itviec_indices), r.get("title", "")[:35], len(desc))
            else:
                log.warning("  [%d/%d] ITviec failed: %s", count, len(itviec_indices), url)
            time.sleep(0.4)

    # 2. Fill TopCV rows using Playwright
    topcv_indices = [i for i in empty_indices if rows[i].get("source_website") == "TopCV"]
    log.info("Filling %d TopCV jobs using Playwright Chromium...", len(topcv_indices))

    if topcv_indices:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=DEFAULT_HEADERS["User-Agent"])
            for count, idx in enumerate(topcv_indices, 1):
                r = rows[idx]
                url = r.get("job_posting_url", "")
                if not url:
                    continue
                try:
                    page.goto(url, timeout=20000, wait_until="commit")
                    try:
                        page.wait_for_selector(".box-job-information-detail-item__title, h2", timeout=12000)
                    except Exception:
                        pass
                    soup = BeautifulSoup(page.content(), "lxml")
                    desc = ""
                    req = ""

                    # TopCV modern layout: .box-job-information-detail-item__title + next sibling div
                    for h in soup.find_all(["h2", "h3"]):
                        htext = h.get_text(" ", strip=True).lower()
                        title_div = h.find_parent("div", class_=lambda c: c and "box-job-information-detail-item__title" in c)
                        if title_div:
                            content_div = title_div.find_next_sibling("div")
                            if content_div:
                                text = content_div.get_text("\n", strip=True)
                                if "mô tả công việc" in htext and not desc:
                                    desc = text
                                elif "yêu cầu ứng viên" in htext and not req:
                                    req = text

                    # Fallback if structure is classic
                    if not desc:
                        for h in soup.find_all(["h2", "h3"]):
                            htext = h.get_text(" ", strip=True).lower()
                            if "mô tả công việc" in htext:
                                p = h.find_parent("div")
                                if p and len(p.get_text(strip=True)) > 100:
                                    desc = p.get_text("\n", strip=True).removeprefix("Mô tả công việc").strip()
                                    break

                    if desc:
                        r["description"] = desc[:8000]
                        if req and not r.get("skills_desc"):
                            r["skills_desc"] = req[:8000]
                        log.info("  [%d/%d] TopCV filled: %s (desc %d chars)", count, len(topcv_indices), r.get("title", "")[:35], len(desc))
                    else:
                        log.warning("  [%d/%d] TopCV empty: %s", count, len(topcv_indices), url)
                except Exception as exc:
                    log.error("  [%d/%d] TopCV error on %s: %s", count, len(topcv_indices), url, exc)
                time.sleep(0.3)
            browser.close()

    # Re-evaluate is_english
    for r in rows:
        r["is_english"] = str(is_english(r.get("title"), r.get("description"), r.get("skills_desc")))

    # Save updated rows back to CSV
    with target.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    filled = sum(1 for r in rows if r.get("description", "").strip())
    log.info("Done! Jobs with description: %d/%d (%.1f%%)", filled, len(rows), filled / len(rows) * 100)


if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else "data/jobs.csv"
    run(p)
