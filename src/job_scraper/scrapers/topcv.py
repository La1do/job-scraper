"""TopCV scraper (www.topcv.vn).

Listing pages render server-side HTML. Each job card carries a stable id in
the job detail URL: /viec-lam/<slug>/<id>.html
"""

from __future__ import annotations

import logging
import re
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from job_scraper.models import JobRecord
from job_scraper.scrapers.base import BaseScraper
from job_scraper.utils.lang_detector import is_english
from job_scraper.utils.salary_parser import parse_salary

log = logging.getLogger("job_scraper")

_SEARCH_URL = "https://www.topcv.vn/tim-viec-lam-{keyword}"
_ID_RE = re.compile(r"/(\d+)\.html")


class TopCVScraper(BaseScraper):
    source_website = "TopCV"
    posting_domain = "topcv.vn"

    def scrape(self, keyword: str, pages: int, fast: bool) -> list[JobRecord]:
        records: list[JobRecord] = []
        slug = quote_plus(keyword.strip()) if keyword.strip() else ""
        for page in range(1, pages + 1):
            url = _SEARCH_URL.format(keyword=slug) if slug else "https://www.topcv.vn/viec-lam"
            html = self.fetch(url, params={"page": page} if page > 1 else None)
            if not html:
                continue
            page_records = self.parse_listing(html)
            log.info("topcv page %d: %d jobs", page, len(page_records))
            if not fast:
                for rec in page_records:
                    self._fill_detail(rec)
            records.extend(page_records)
        return records

    def parse_listing(self, html: str) -> list[JobRecord]:
        soup = BeautifulSoup(html, "lxml")
        records: list[JobRecord] = []
        for card in soup.select("div.job-item-search-result, div.job-item"):
            title_a = next(
                (a for a in card.find_all("a") if "/viec-lam/" in a.get("href", "") and a.get_text(strip=True)),
                None,
            )
            if not title_a:
                continue
            url = title_a.get("href", "").split("?")[0]
            if not url.startswith("http"):
                url = "https://www.topcv.vn" + url
            match = _ID_RE.search(url)
            job_id = f"topcv_{match.group(1)}" if match else f"topcv_{abs(hash(url)) % 10**10}"

            company_a = card.select_one("a.company-name, a[href*='/cong-ty/'], .company-name")
            company = company_a.get_text(strip=True) if company_a else ""

            salary_el = card.select_one(".title-salary, .salary, label.salary")
            salary_text = salary_el.get_text(" ", strip=True) if salary_el else ""
            salary = parse_salary(salary_text)

            location_el = card.select_one(".address, .city, label.address")
            location = location_el.get_text(" ", strip=True) if location_el else ""

            exp_el = card.select_one(".exp, .experience")
            experience = exp_el.get_text(" ", strip=True) if exp_el else ""

            title = title_a.get_text(" ", strip=True)
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
                job_posting_url=url,
                formatted_experience_level=experience,
                posting_domain=self.posting_domain,
                source_website=self.source_website,
                is_english=str(is_english(title)),
            )
            records.append(rec)
        return records

    def _fill_detail(self, rec: JobRecord) -> None:
        html = self.fetch(rec.job_posting_url)
        if not html:
            return
        soup = BeautifulSoup(html, "lxml")
        desc = soup.select_one("div.job-description, div.job-data, #job-description")
        if desc:
            rec.description = desc.get_text("\n", strip=True)[:8000]

        # Extract raw original candidate requirements section
        req = soup.select_one("div.job-requirements, div.job-data:nth-of-type(2)")
        if not req:
            for h in soup.find_all(["h2", "h3", "h4"]):
                if any(k in h.get_text(" ", strip=True).lower() for k in ["yêu cầu ứng viên", "yêu cầu"]):
                    parent = h.find_parent("div")
                    if parent:
                        req = parent
                        break
        if req:
            rec.skills_desc = req.get_text("\n", strip=True)[:8000]
        else:
            skills = [t.get_text(strip=True) for t in soup.select(".job-tags a, .box-category a, .keyword a")]
            if skills:
                rec.skills_desc = ", ".join(dict.fromkeys(skills))

        deadline = soup.select_one(".deadline, .job-deadline")
        if deadline:
            rec.expiry = deadline.get_text(" ", strip=True)
        rec.is_english = str(is_english(rec.title, rec.description, rec.skills_desc))
