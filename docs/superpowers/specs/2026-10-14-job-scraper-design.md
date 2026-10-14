# Job Scraper System Design Specification

- **Date:** 2026-10-14
- **Project Location:** `/home/truongdb/job-scraper`
- **Output:** Unified CSV file with 30 standardized fields

---

## 1. Overview & Objectives

Build a modular Python CLI web scraper to extract job postings from Vietnamese tech job platforms (TopCV, ITviec) as well as custom generic URLs, normalizing the extracted records into a single unified CSV file formatted for analysis.

### Core Requirements
1. Extract job listings from TopCV (`topcv.vn`), ITviec (`itviec.com`), and arbitrary job URLs (Generic scraper via HTML / JSON-LD `schema.org/JobPosting`).
2. Map all extracted data into a unified 30-column CSV schema based on the LinkedIn Job Postings standard plus source website and language detection.
3. Support incremental append mode with deduplication based on `job_id` or `job_posting_url`.
4. Detect whether the job posting is written in English (`is_english = True/False`).
5. Export CSV with `utf-8-sig` encoding (Excel-compatible with Vietnamese diacritics).
6. Simple CLI interface with options for keywords, page counts, output file, and custom URLs.

---

## 2. Standardized CSV Schema (30 Columns)

| Field Name | Type | Description | Example |
|---|---|---|---|
| `job_id` | str | Unique identifier of the job | `topcv_123456`, `itviec_backend-dev-xyz` |
| `company_id` | str | Company identifier or company slug | `fpt-software` |
| `title` | str | Job title | `Senior Python Backend Engineer` |
| `description` | str | Full or excerpt job description | `We are looking for...` |
| `max_salary` | float/str | Maximum salary if parsed | `25000000` or `2500` |
| `med_salary` | float/str | Median / estimated salary | `20000000` |
| `min_salary` | float/str | Minimum salary if parsed | `15000000` |
| `pay_period` | str | Payment frequency | `MONTH`, `YEAR`, `HOUR` |
| `formatted_work_type` | str | Work type | `Full-time`, `Part-time`, `Contract` |
| `location` | str | Work location / city | `Hà Nội`, `Hồ Chí Minh`, `Hybrid` |
| `applies` | str/int | Number of applicants | `12` |
| `original_listed_time`| str | Original posting timestamp | `2026-10-01` |
| `remote_allowed` | bool/int | Remote work flag | `1` or `0` |
| `views` | str/int | View count | `150` |
| `job_posting_url` | str | Canonical URL of posting | `https://topcv.vn/viec-lam/...` |
| `application_url` | str | Direct application URL | `https://...` |
| `application_type` | str | In-app or external | `Direct`, `External` |
| `expiry` | str | Application deadline | `2026-11-01` |
| `closed_time` | str | Time job closed | `` |
| `formatted_experience_level` | str | Experience level | `Junior`, `Middle`, `Senior`, `Lead` |
| `skills_desc` | str | Required skills/tags | `Python, Django, PostgreSQL, Docker` |
| `listed_time` | str | Published time | `2026-10-10` |
| `posting_domain` | str | Domain of posting | `topcv.vn`, `itviec.com` |
| `sponsored` | int | Paid / featured post | `0` or `1` |
| `work_type` | str | Code/enum for work type | `FULL_TIME` |
| `currency` | str | Currency code | `VND`, `USD` |
| `compensation_type`| str | Fixed salary, commission, etc. | `BASE_SALARY` |
| `source_website` | str | Display source name | `TopCV`, `ITviec`, `Generic` |
| `is_english` | bool | Whether job post is in English | `True` or `False` |
| `scraped` | str | Timestamp when record was scraped | `2026-10-14T10:30:00Z` |

---

## 3. Architecture & Components

```text
job-scraper/
├── pyproject.toml
├── README.md
├── src/
│   └── job_scraper/
│       ├── __init__.py
│       ├── __main__.py          # Entry point (python -m job_scraper)
│       ├── cli.py               # CLI parser & execution flow
│       ├── models.py            # JobRecord dataclass & column definitions
│       ├── utils/
│       │   ├── __init__.py
│       │   ├── salary_parser.py # Normalizes Vietnamese/English salary strings
│       │   └── lang_detector.py # Checks Vietnamese diacritics & English tokens
│       ├── scrapers/
│       │   ├── __init__.py
│       │   ├── base.py          # Abstract BaseScraper
│       │   ├── topcv.py         # TopCV HTML scraper
│       │   ├── itviec.py        # ITviec scraper
│       │   └── generic.py       # Generic URL scraper (JSON-LD + meta tags + selectors)
│       └── storage/
│           ├── __init__.py
│           └── csv_writer.py    # Append + deduplicate + UTF-8-BOM writer
└── tests/
    ├── test_models.py
    ├── test_salary_parser.py
    ├── test_lang_detector.py
    ├── test_csv_writer.py
    └── fixtures/
```

### Module Responsibilities

1. **`models.py`**:
   - `JobRecord`: Python dataclass holding the 30 fields with default values.
   - `to_dict()`: Converts to dict matching `COLUMNS` sequence.
   - `COLUMNS`: Constant list of 30 column names.

2. **`utils/salary_parser.py`**:
   - Parses phrases like `"15 - 25 triệu"`, `"Tới 40 triệu"`, `"$1,500 - $3,000"`, `"Thỏa thuận"`.
   - Extracts `min_salary`, `max_salary`, `currency`, `pay_period`.

3. **`utils/lang_detector.py`**:
   - Inspects `title` + `description` + `skills_desc`.
   - If contains Vietnamese accented characters (`à, á, ả, ã, ạ, ă, ắ, ằ, ẵ, ặ, â, ấ, ầ, ...`) -> `is_english = False`.
   - If no Vietnamese diacritics and matches common English job keywords (`requirements`, `experience`, `skills`, `we are looking for`, `responsibilities`) -> `is_english = True`.

4. **`scrapers/base.py`**:
   - Defines interface: `scrape(keyword: str, pages: int) -> List[JobRecord]`.
   - Handles HTTP headers (User-Agent rotation), retry logic with `httpx`.

5. **`scrapers/topcv.py`**:
   - Queries `https://www.topcv.vn/tim-viec-lam-[keyword]` or general search endpoint.
   - Parses job items: `title`, `company`, `salary`, `location`, `url`, `exp`, `deadline`.
   - Optional detail fetcher for full description.

6. **`scrapers/itviec.py`**:
   - Queries `https://itviec.com/it-jobs/[keyword]`.
   - Parses job cards: `title`, `company`, `skills`, `salary`, `url`, `remote_allowed`.

7. **`scrapers/generic.py`**:
   - Takes arbitrary URL.
   - First looks for `<script type="application/ld+json">` containing `JobPosting` schema.
   - Fallback: extracts OpenGraph meta tags (`og:title`, `og:description`, `og:url`), `<title>`, and main content.

8. **`storage/csv_writer.py`**:
   - Reads existing CSV (if exists) into memory set of seen `job_id` / `job_posting_url`.
   - Appends only new unseen records.
   - Writes with `encoding='utf-8-sig'`, `lineterminator='\n'`.

---

## 4. CLI Usage Specification

```bash
# Crawl TopCV
python -m job_scraper --source topcv --keyword "python" --pages 2 -o jobs.csv

# Crawl ITviec
python -m job_scraper --source itviec --keyword "golang" --pages 1 -o jobs.csv

# Crawl custom URL
python -m job_scraper --source generic --url "https://example.com/careers/123" -o jobs.csv

# Crawl without detail page fetching (fast mode)
python -m job_scraper --source topcv --keyword "react" --pages 1 --fast -o jobs.csv
```

---

## 5. Error Handling & Edge Cases

- **Anti-bot / Cloudflare / 403**: Graceful warning log with suggestion to use cookies or `--browser` mode.
- **Network Timeout**: Retry up to 3 times before skipping item/page.
- **Empty / Incomplete DOM**: Fallback defaults (`None` or empty strings) without throwing uncaught exceptions.
- **CSV Concurrency / File lock**: Catch `PermissionError` (e.g. if open in Excel on Windows) and report cleanly to user.

---

## 6. Testing Strategy

- Unit tests for:
  - `salary_parser`: Vietnamese million VND, USD ranges, negotiate/thỏa thuận.
  - `lang_detector`: Vietnamese posts, English posts, mixed posts.
  - `csv_writer`: Headers, deduplication on append, UTF-8-BOM signature.
  - `models`: Serialization order and completeness.
- Mock HTML fixtures for TopCV & ITviec parsers (offline unit tests, no external network dependencies).
