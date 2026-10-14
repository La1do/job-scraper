"""Generic scraper for an arbitrary job URL.

Priority:
1. schema.org JobPosting JSON-LD blocks.
2. OpenGraph / meta tags plus the page <title> and main text.
"""

from __future__ import annotations

import json
import logging
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from job_scraper.models import JobRecord
from job_scraper.scrapers.base import BaseScraper
from job_scraper.utils.lang_detector import is_english
from job_scraper.utils.salary_parser import parse_salary

log = logging.getLogger("job_scraper")


class GenericScraper(BaseScraper):
    source_website = "Generic"

    def __init__(self, url: str, timeout: float = 20.0, retries: int = 3) -> None:
        super().__init__(timeout=timeout, retries=retries)
        self.url = url
        self.posting_domain = urlparse(url).netloc.removeprefix("www.")

    def scrape(self, keyword: str, pages: int, fast: bool) -> list[JobRecord]:
        html = self.fetch(self.url)
        if not html:
            return []
        records = self.parse(html, self.url)
        log.info("generic %s: %d jobs", self.url, len(records))
        return records

    def parse(self, html: str, page_url: str) -> list[JobRecord]:
        soup = BeautifulSoup(html, "lxml")
        domain = urlparse(page_url).netloc.removeprefix("www.")
        records = self._from_jsonld(soup, domain)
        if records:
            return records
        return [self._from_meta(soup, page_url, domain)]

    def _from_jsonld(self, soup: BeautifulSoup, domain: str) -> list[JobRecord]:
        records: list[JobRecord] = []
        for script in soup.select("script[type='application/ld+json']"):
            try:
                data = json.loads(script.string or "")
            except (json.JSONDecodeError, TypeError):
                continue
            for node in _flatten(data):
                types = node.get("@type", "")
                if isinstance(types, list):
                    is_job = "JobPosting" in types
                else:
                    is_job = types == "JobPosting"
                if is_job:
                    records.append(self._record_from_jobposting(node, domain))
        return records

    def _record_from_jobposting(self, node: dict, domain: str) -> JobRecord:
        org = node.get("hiringOrganization") or {}
        company = org.get("name", "") if isinstance(org, dict) else ""
        place = node.get("jobLocation") or {}
        location = ""
        if isinstance(place, dict):
            address = place.get("address") or {}
            if isinstance(address, dict):
                location = ", ".join(
                    p for p in (address.get("addressLocality", ""), address.get("addressCountry", "")) if p
                )
            elif isinstance(address, str):
                location = address
        elif isinstance(place, list) and place:
            location = str(place[0])

        salary_node = node.get("baseSalary") or {}
        salary_text = ""
        if isinstance(salary_node, dict):
            value = salary_node.get("value") or {}
            if isinstance(value, dict):
                lo = value.get("minValue", "")
                hi = value.get("maxValue", "")
                unit = value.get("unitText", "")
                cur = salary_node.get("currency", "")
                salary_text = f"{lo} - {hi} {cur} {unit}".strip()
        salary = parse_salary(salary_text) if salary_text else parse_salary("")

        title = str(node.get("title", ""))
        description = _strip(str(node.get("description", "")))
        url = str(node.get("url", ""))
        skills = node.get("skills")
        skills_desc = ", ".join(skills) if isinstance(skills, list) else str(skills or "")

        return JobRecord(
            job_id=f"generic_{abs(hash(url or title)) % 10**12}",
            company_id=company,
            title=title,
            description=description[:8000],
            min_salary=salary.min_salary,
            max_salary=salary.max_salary,
            med_salary=salary.med_salary,
            pay_period=salary.pay_period or _map_unit(salary_node),
            currency=salary.currency,
            compensation_type=salary.compensation_type,
            formatted_work_type=str(node.get("employmentType", "")),
            work_type=str(node.get("employmentType", "")),
            location=location,
            job_posting_url=url,
            application_url=str(node.get("directApply", "")) if node.get("directApply") else url,
            expiry=str(node.get("validThrough", "")),
            listed_time=str(node.get("datePosted", "")),
            original_listed_time=str(node.get("datePosted", "")),
            skills_desc=skills_desc,
            posting_domain=domain,
            source_website=self.source_website,
            is_english=str(is_english(title, description)),
        )

    def _from_meta(self, soup: BeautifulSoup, page_url: str, domain: str) -> JobRecord:
        def meta(prop: str) -> str:
            tag = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
            return tag.get("content", "").strip() if tag else ""

        title = meta("og:title") or (soup.title.get_text(strip=True) if soup.title else "")
        description = meta("og:description") or meta("description")
        main = soup.select_one("main, article, div.content, div.job-description")
        if main and not description:
            description = main.get_text("\n", strip=True)[:4000]
        return JobRecord(
            job_id=f"generic_{abs(hash(page_url)) % 10**12}",
            title=title,
            description=description[:8000],
            job_posting_url=meta("og:url") or page_url,
            posting_domain=domain,
            source_website=self.source_website,
            is_english=str(is_english(title, description)),
        )


def _flatten(data: object) -> list[dict]:
    out: list[dict] = []
    if isinstance(data, dict):
        graph = data.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                out.extend(_flatten(item))
        else:
            out.append(data)
    elif isinstance(data, list):
        for item in data:
            out.extend(_flatten(item))
    return out


def _strip(html_text: str) -> str:
    if "<" not in html_text:
        return html_text.strip()
    return BeautifulSoup(html_text, "lxml").get_text("\n", strip=True)


def _map_unit(salary_node: object) -> str:
    if not isinstance(salary_node, dict):
        return ""
    value = salary_node.get("value") or {}
    unit = (value.get("unitText", "") if isinstance(value, dict) else "").upper()
    return {"MONTH": "MONTH", "YEAR": "YEAR", "HOUR": "HOUR", "DAY": "DAY"}.get(unit, "")
