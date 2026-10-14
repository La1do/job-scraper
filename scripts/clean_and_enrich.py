"""Deep clean and keyword enrichment for data/jobs.csv.

Visits job URLs to:
1. Verify validity (delete 404, expired, empty, spam, or too-short JDs).
2. Extract full job description.
3. Extract precise professional skills/keywords (replacing welfare items like 'Đồng phục', 'Du lịch').
4. Fill missing company names.
5. Re-evaluate is_english and salary parsing.
6. Save clean dataset back to CSV and push.
"""

from __future__ import annotations

import csv
import logging
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from job_scraper.models import COLUMNS, JobRecord
from job_scraper.scrapers.base import DEFAULT_HEADERS
from job_scraper.utils.lang_detector import is_english
from job_scraper.utils.salary_parser import parse_salary

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("clean_enrich")

# Comprehensive keyword catalog for IT, Marketing, Sales, Design, Finance, HR
KEYWORDS_CATALOG = [
    # IT & Software
    "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", ".NET", "Golang", "Go", "PHP", "Laravel",
    "Ruby", "Rust", "Swift", "Kotlin", "Flutter", "React Native", "React", "ReactJS", "Vue", "VueJS",
    "Angular", "NextJS", "Next.js", "NodeJS", "Node.js", "NestJS", "Express", "Django", "FastAPI",
    "Spring Boot", "SQL", "MySQL", "PostgreSQL", "MongoDB", "Redis", "Elasticsearch", "Kafka", "RabbitMQ",
    "Docker", "Kubernetes", "K8s", "AWS", "Azure", "GCP", "CI/CD", "Linux", "Git", "DevOps",
    "Microservices", "RESTful API", "GraphQL", "Machine Learning", "Deep Learning", "NLP", "LLM",
    "AI", "Data Analyst", "Data Engineer", "Data Science", "Power BI", "Tableau", "Excel",
    "QA", "QC", "Automation Test", "Manual Test", "Selenium", "Cybersecurity", "Penetration Testing",
    "Sysadmin", "OOP", "Agile", "Scrum",
    # Marketing & Creative
    "Digital Marketing", "SEO", "SEM", "Content Marketing", "Content Creator", "Social Media",
    "Facebook Ads", "Google Ads", "TikTok Ads", "Performance Marketing", "Email Marketing",
    "Trade Marketing", "Brand Marketing", "Copywriting", "PR", "Truyền thông", "Event",
    "Video Editing", "Graphic Design", "Photoshop", "Illustrator", "Premiere", "Canva", "CapCut",
    "UI/UX", "Figma", "Google Analytics", "CRM", "Kế hoạch Marketing", "Nghiên cứu thị trường",
    "Influencer Marketing", "KOL", "Livestream", "Affiliate Marketing",
    # Sales & Business
    "B2B", "B2C", "Telesales", "Account Executive", "Business Development", "Chăm sóc khách hàng",
    "Đàm phán", "Kinh doanh", "Quản lý doanh số", "Bán hàng", "Thương mại điện tử", "E-commerce",
    # Finance, HR, Admin
    "Kế toán tổng hợp", "Kế toán thuế", "Báo cáo tài chính", "Kiểm toán", "Tuyển dụng", "C&B", "Nhân sự",
    "Đào tạo", "Luật lao động", "Hành chính",
]

_WELFARE_TERMS = {
    "chế độ bảo hiểm", "du lịch", "đồng phục", "phụ cấp", "đào tạo",
    "chế độ thưởng", "chăm sóc sức khỏe", "tăng lương", "nghỉ phép năm",
    "laptop", "clb thể thao", "thưởng", "thưởng tháng 13", "bảo hiểm",
}


def extract_keywords(text: str) -> list[str]:
    found = []
    seen = set()
    low = text.lower()
    for kw in KEYWORDS_CATALOG:
        pat = r"(?<![a-zA-Z0-9_])" + re.escape(kw.lower()) + r"(?![a-zA-Z0-9_])"
        if re.search(pat, low):
            norm = kw.replace("ReactJS", "React").replace("VueJS", "Vue").replace("Node.js", "NodeJS")
            if norm.lower() not in seen:
                seen.add(norm.lower())
                found.append(norm)
    return found


def is_welfare_only(skills_desc: str) -> bool:
    if not skills_desc:
        return True
    parts = [p.strip().lower() for p in skills_desc.split(",") if p.strip()]
    if not parts:
        return True
    return all(any(w in p for w in _WELFARE_TERMS) for p in parts)


def fetch_url(url: str, timeout: float = 12.0) -> tuple[int, str]:
    try:
        with httpx.Client(headers=DEFAULT_HEADERS, timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url)
            return resp.status_code, resp.text
    except Exception as exc:
        return 0, str(exc)


def enrich_row(row: dict[str, str]) -> tuple[dict[str, str] | None, str]:
    """Process a single job row. Returns (cleaned_row, reason).

    If row should be deleted, returns (None, reason).
    """
    title = row.get("title", "").strip()
    url = row.get("job_posting_url", "").strip()
    source = row.get("source_website", "").strip()

    # Gate 1: basic sanity
    if not title or len(title) < 5:
        return None, "empty or too short title"
    if not url or not url.startswith("http"):
        return None, "invalid URL"

    # Only fetch detail if description is empty or skills are welfare-only
    needs_fetch = not row.get("description") or is_welfare_only(row.get("skills_desc", ""))

    page_html = ""
    if needs_fetch:
        status, page_html = fetch_url(url)
        # Gate 2: HTTP status failure
        if status in (404, 410, 500, 502, 503):
            return None, f"HTTP {status}"

        # Gate 3: Expired or removed job (check visible text, not embedded scripts)
        soup_temp = BeautifulSoup(page_html, "lxml")
        title_tag = soup_temp.title.get_text(strip=True).lower() if soup_temp.title else ""
        if "404" in title_tag or "không tìm thấy" in title_tag or "not found" in title_tag:
            return None, "404 page title"

        # Check explicit banner warning
        banner = soup_temp.select_one(".expired-job, .job-closed, .alert-expired, .box-job-closed")
        if banner and any(w in banner.get_text(strip=True).lower() for w in ["hết hạn", "đã đóng", "expired", "closed"]):
            return None, "explicit expired banner"

    # If we have HTML, extract rich fields
    if page_html:
        soup = BeautifulSoup(page_html, "lxml")

        # CareerViet specific extraction
        if "careerviet.vn" in url:
            desc_text = ""
            req_text = ""
            for h in soup.find_all(["h2", "h3", "h4"]):
                htext = h.get_text(" ", strip=True).lower()
                parent = h.find_parent("div")
                if not parent:
                    continue
                body = parent.get_text("\n", strip=True)
                if any(k in htext for k in ["mô tả công việc", "job description"]):
                    desc_text = body
                elif any(k in htext for k in ["yêu cầu công việc", "job requirement", "yêu cầu"]):
                    req_text = body

            if desc_text and not row.get("description"):
                row["description"] = desc_text[:8000]

            # Extract keywords from title + requirements + description
            combined_text = f"{title} {req_text} {desc_text}"
            kws = extract_keywords(combined_text)
            if kws:
                row["skills_desc"] = ", ".join(kws)

            # Extract company if missing
            if not row.get("company_id"):
                comp_el = soup.select_one("a.company-name, .employer-name")
                if comp_el:
                    row["company_id"] = comp_el.get_text(strip=True)

        # ITviec specific extraction
        elif "itviec.com" in url:
            desc_el = soup.select_one("div.job-description, div[class*='job-content']")
            if desc_el and not row.get("description"):
                row["description"] = desc_el.get_text("\n", strip=True)[:8000]

            combined_text = f"{title} {row.get('description', '')} {row.get('skills_desc', '')}"
            kws = extract_keywords(combined_text)
            if kws:
                # Merge existing tags with extracted
                existing = [k.strip() for k in row.get("skills_desc", "").split(",") if k.strip()]
                all_kws = list(dict.fromkeys(existing + kws))
                row["skills_desc"] = ", ".join(all_kws)

            # Company fallback from slug
            if not row.get("company_id"):
                comp_el = soup.select_one("span a[href*='/companies/'], a[href*='/companies/']")
                if comp_el and comp_el.get_text(strip=True):
                    row["company_id"] = comp_el.get_text(strip=True)

    # If still welfare-only, extract from title
    if is_welfare_only(row.get("skills_desc", "")):
        kws = extract_keywords(f"{title} {row.get('description', '')}")
        row["skills_desc"] = ", ".join(kws) if kws else ""

    # Gate 4: If after all extraction, job has neither description nor skills nor company -> delete bad JD
    if not row.get("description") and not row.get("skills_desc") and not row.get("company_id"):
        return None, "empty JD (no description, no skills, no company)"

    # Update metadata
    row["is_english"] = str(is_english(row.get("title"), row.get("description"), row.get("skills_desc")))
    if not row.get("min_salary") and not row.get("max_salary"):
        # try parsing from text
        s = parse_salary(f"{title} {row.get('description', '')[:500]}")
        if s.currency:
            row["min_salary"] = s.min_salary
            row["max_salary"] = s.max_salary
            row["med_salary"] = s.med_salary
            row["currency"] = s.currency
            row["pay_period"] = s.pay_period

    return row, "ok"


def run(csv_path: str = "data/jobs.csv", workers: int = 10) -> None:
    target = Path(csv_path)
    if not target.exists():
        log.error("File not found: %s", target)
        return

    with target.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

    total = len(rows)
    log.info("Starting enrichment & cleaning for %d jobs with %d workers...", total, workers)
    start = time.time()

    cleaned_rows: list[dict[str, str]] = []
    deleted_reasons: dict[str, int] = {}
    completed = 0

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {executor.submit(enrich_row, r): r for r in rows}
        for future in as_completed(future_map):
            completed += 1
            if completed % 50 == 0 or completed == total:
                log.info("Progress: %d/%d (%.1f%%) in %.1fs", completed, total, completed / total * 100, time.time() - start)
            try:
                res, reason = future.result()
                if res is not None:
                    cleaned_rows.append(res)
                else:
                    deleted_reasons[reason] = deleted_reasons.get(reason, 0) + 1
            except Exception as exc:
                deleted_reasons[f"exception: {exc}"] = deleted_reasons.get(f"exception: {exc}", 0) + 1

    # Deduplicate final list by job_id then job_posting_url
    final_rows: list[dict[str, str]] = []
    seen_ids = set()
    seen_urls = set()
    for r in cleaned_rows:
        jid = r.get("job_id", "")
        url = r.get("job_posting_url", "")
        if (jid and jid in seen_ids) or (url and url in seen_urls):
            deleted_reasons["duplicate in final"] = deleted_reasons.get("duplicate in final", 0) + 1
            continue
        final_rows.append(r)
        if jid:
            seen_ids.add(jid)
        if url:
            seen_urls.add(url)

    # Write cleaned rows back to CSV
    with target.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for r in final_rows:
            writer.writerow(r)

    elapsed = time.time() - start
    log.info("=== ENRICHMENT & CLEANING SUMMARY ===")
    log.info("Total input:   %d jobs", total)
    log.info("Total cleaned: %d jobs (kept)", len(final_rows))
    log.info("Total deleted: %d jobs", total - len(final_rows))
    for reason, count in sorted(deleted_reasons.items(), key=lambda x: -x[1]):
        log.info("  - Deleted (%s): %d", reason, count)
    log.info("Finished in %.1fs -> %s", elapsed, target)


if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else "data/jobs.csv"
    run(p)
