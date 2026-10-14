"""ITviec scraper (itviec.com).

Search results are server-rendered. Job cards link to /it-jobs/<slug>.
"""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from job_scraper.models import JobRecord
from job_scraper.scrapers.base import BaseScraper
from job_scraper.utils.lang_detector import is_english
from job_scraper.utils.salary_parser import parse_salary

log = logging.getLogger("job_scraper")

_SEARCH_URL = "https://itviec.com/it-jobs"


class ITViecScraper(BaseScraper):
    source_website = "ITviec"
    posting_domain = "itviec.com"

    def scrape(self, keyword: str, pages: int, fast: bool) -> list[JobRecord]:
        records: list[JobRecord] = []
        for page in range(1, pages + 1):
            params: dict[str, str | int] = {}
            if keyword.strip():
                params["query"] = keyword.strip()
            if page > 1:
                params["page"] = page
            html = self.fetch(_SEARCH_URL, params=params or None)
            if not html:
                continue
            page_records = self.parse_listing(html)
            log.info("itviec page %d: %d jobs", page, len(page_records))
            if not fast:
                for rec in page_records:
                    self._fill_detail(rec)
            records.extend(page_records)
        return records

    def parse_listing(self, html: str) -> list[JobRecord]:
        soup = BeautifulSoup(html, "lxml")
        records: list[JobRecord] = []
        seen: set[str] = set()
        for card in soup.select("div.job, div.job-card, div[class*='job-card']"):
            title_a = card.select_one("h3 a[href*='/it-jobs/'], a[href*='/it-jobs/']")
            if not title_a:
                continue
            href = title_a.get("href", "").split("?")[0]
            if not href or href in seen:
                continue
            seen.add(href)
            url = href if href.startswith("http") else "https://itviec.com" + href
            slug = href.rstrip("/").rsplit("/", 1)[-1]
            job_id = f"itviec_{slug}"

            title = title_a.get_text(" ", strip=True)
            company_el = next(
                (a for a in card.find_all("a") if "/companies/" in a.get("href", "") and a.get_text(strip=True)),
                None,
            )
            company = company_el.get_text(" ", strip=True) if company_el else ""

            salary_el = card.select_one(".salary, .text-salary")
            salary = parse_salary(salary_el.get_text(" ", strip=True) if salary_el else "")

            location_el = card.select_one(".location, .city, .text-location")
            location = location_el.get_text(" ", strip=True) if location_el else ""

            tags = [t.get_text(strip=True) for t in card.select(".tag, .skill-tag, a.itag")]
            remote = "1" if any("remote" in t.lower() or "hybrid" in t.lower() for t in tags + [location]) else "0"

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
                remote_allowed=remote,
                skills_desc=", ".join(dict.fromkeys(tags)),
                job_posting_url=url,
                posting_domain=self.posting_domain,
                source_website=self.source_website,
                is_english=str(is_english(title, " ".join(tags))),
            )
            records.append(rec)
        return records

    def _fill_detail(self, rec: JobRecord) -> None:
        html = self.fetch(rec.job_posting_url)
        if not html:
            return
        soup = BeautifulSoup(html, "lxml")
        desc = soup.select_one("div.job-description, div[class*='job-content'], .paragraph")
        if desc:
            rec.description = desc.get_text("\n", strip=True)[:8000]
        rec.is_english = str(is_english(rec.title, rec.description, rec.skills_desc))
