"""CareerViet scraper (careerviet.vn, former CareerBuilder).

Server-rendered listing with ~50 jobs per page. Fast and reliable for
Marketing, IT, Sales, HR, Finance, and other fields.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import quote

from bs4 import BeautifulSoup

from job_scraper.models import JobRecord
from job_scraper.scrapers.base import BaseScraper
from job_scraper.utils.lang_detector import is_english
from job_scraper.utils.salary_parser import parse_salary

log = logging.getLogger("job_scraper")


class CareerVietScraper(BaseScraper):
    source_website = "CareerViet"
    posting_domain = "careerviet.vn"

    def scrape(self, keyword: str, pages: int, fast: bool = True) -> list[JobRecord]:
        records: list[JobRecord] = []
        slug = quote(keyword.strip().lower().replace(" ", "-")) if keyword.strip() else ""
        for page in range(1, pages + 1):
            if slug:
                # CareerViet keyword pagination: /viec-lam/<slug>-k-trang-<page>-vi.html
                if page == 1:
                    url = f"https://careerviet.vn/viec-lam/{slug}-k-vi.html"
                else:
                    url = f"https://careerviet.vn/viec-lam/{slug}-k-trang-{page}-vi.html"
            else:
                if page == 1:
                    url = "https://careerviet.vn/tim-viec-lam.html"
                else:
                    url = f"https://careerviet.vn/tim-viec-lam-trang-{page}.html"

            html = self.fetch(url)
            if not html:
                continue
            page_records = self.parse_listing(html)
            log.info("careerviet '%s' page %d: %d jobs", keyword or "all", page, len(page_records))
            if not page_records:
                break
            records.extend(page_records)
        return records

    def parse_listing(self, html: str) -> list[JobRecord]:
        soup = BeautifulSoup(html, "lxml")
        records: list[JobRecord] = []
        for card in soup.select(".job-item"):
            link_a = card.select_one("a.job_link")
            if not link_a:
                continue
            href = link_a.get("href", "").split("?")[0]
            if not href.startswith("http"):
                href = "https://careerviet.vn" + href

            raw_id = card.get("id", "") or link_a.get("data-id", "")
            clean_id = raw_id.removeprefix("job-item-")
            job_id = f"careerviet_{clean_id}" if clean_id else f"careerviet_{abs(hash(href)) % 10**10}"

            title = link_a.get("title", "") or link_a.get_text(" ", strip=True)
            # Remove any trailing salary/location text if title grabbed full content
            title = title.split("\n")[0].strip()

            comp_a = card.select_one("a.company-name")
            company = (comp_a.get("title") or comp_a.get_text(strip=True)) if comp_a else ""

            salary_el = card.select_one(".salary, div.salary p")
            salary_raw = salary_el.get_text(" ", strip=True).removeprefix("Lương:").strip() if salary_el else ""
            salary = parse_salary(salary_raw)

            loc_el = card.select_one(".location")
            location = loc_el.get_text(" ", strip=True) if loc_el else ""

            time_el = card.select_one(".time")
            expiry = ""
            listed = ""
            if time_el:
                times = time_el.find_all("time")
                if len(times) >= 1:
                    expiry = times[0].get_text(strip=True)
                if len(times) >= 2:
                    listed = times[1].get_text(strip=True)

            welfare_items = [li.get_text(strip=True) for li in card.select(".welfare li")]
            skills_desc = ", ".join(welfare_items)

            rec = JobRecord(
                job_id=job_id,
                company_id=company,
                title=title,
                min_salary=salary.min_salary,
                max_salary=salary.max_salary,
                med_salary=salary.med_salary,
                pay_period=salary.pay_period,
                currency=salary.currency,
                compensation_type=salary.compensation_type,
                location=location,
                expiry=expiry,
                listed_time=listed,
                skills_desc=skills_desc,
                job_posting_url=href,
                posting_domain=self.posting_domain,
                source_website=self.source_website,
                is_english=str(is_english(title)),
            )
            records.append(rec)
        return records
