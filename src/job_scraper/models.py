"""JobRecord: 30-column schema for the unified CSV."""

from __future__ import annotations

from dataclasses import dataclass, asdict, fields
from datetime import datetime, timezone

COLUMNS: list[str] = [
    "job_id",
    "company_id",
    "title",
    "description",
    "max_salary",
    "med_salary",
    "min_salary",
    "pay_period",
    "formatted_work_type",
    "location",
    "applies",
    "original_listed_time",
    "remote_allowed",
    "views",
    "job_posting_url",
    "application_url",
    "application_type",
    "expiry",
    "closed_time",
    "formatted_experience_level",
    "skills_desc",
    "listed_time",
    "posting_domain",
    "sponsored",
    "work_type",
    "currency",
    "compensation_type",
    "source_website",
    "is_english",
    "scraped",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class JobRecord:
    job_id: str = ""
    company_id: str = ""
    title: str = ""
    description: str = ""
    max_salary: str = ""
    med_salary: str = ""
    min_salary: str = ""
    pay_period: str = ""
    formatted_work_type: str = ""
    location: str = ""
    applies: str = ""
    original_listed_time: str = ""
    remote_allowed: str = ""
    views: str = ""
    job_posting_url: str = ""
    application_url: str = ""
    application_type: str = ""
    expiry: str = ""
    closed_time: str = ""
    formatted_experience_level: str = ""
    skills_desc: str = ""
    listed_time: str = ""
    posting_domain: str = ""
    sponsored: str = ""
    work_type: str = ""
    currency: str = ""
    compensation_type: str = ""
    source_website: str = ""
    is_english: str = ""
    scraped: str = ""

    def __post_init__(self) -> None:
        if not self.scraped:
            self.scraped = _now_iso()

    def to_row(self) -> dict[str, str]:
        data = asdict(self)
        return {col: "" if data[col] is None else str(data[col]) for col in COLUMNS}


def empty_record(**overrides: str) -> JobRecord:
    return JobRecord(**overrides)
