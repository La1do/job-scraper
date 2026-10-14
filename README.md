# Job Scraper (TopCV, ITviec, Generic URL -> 1 File CSV)

Cào tin tuyển dụng từ nhiều nguồn đổ về 1 file CSV duy nhất với 30 cột chuẩn hóa (LinkedIn schema mở rộng).

## Tính năng

- **TopCV**: Cào danh sách tin tuyển dụng, tự động bypass anti-bot bằng Chromium headless khi bị 403.
- **ITviec**: Cào danh sách tin tuyển dụng IT theo từ khóa và phân trang.
- **Generic URL**: Nhận bất kỳ URL nào, tự bóc JSON-LD (`schema.org/JobPosting`) hoặc OpenGraph / meta tags.
- **Ghi 1 file CSV chung**:
  - Hỗ trợ append nhiều lần.
  - Tự deduplicate theo `job_id` và `job_posting_url`.
  - Encoding `utf-8-sig` (Excel mở tiếng Việt không lỗi font).
  - Tự động nhận diện tin tiếng Anh (`is_english = True/False`).
  - Chuẩn hóa mức lương (`min_salary`, `max_salary`, `med_salary`, `currency`, `pay_period`).

---

## 30 Cột Trong File CSV

```text
job_id, company_id, title, description, max_salary, med_salary, min_salary,
pay_period, formatted_work_type, location, applies, original_listed_time,
remote_allowed, views, job_posting_url, application_url, application_type,
expiry, closed_time, formatted_experience_level, skills_desc, listed_time,
posting_domain, sponsored, work_type, currency, compensation_type,
source_website, is_english, scraped
```

---

## Cài đặt

```bash
cd /home/truongdb/Desktop/job-scraper

# Kích hoạt venv (nếu dùng terminal riêng)
source .venv/bin/activate

# Cài đặt package editable
uv pip install -e .
```

---

## Cách chạy

### 1. Cào TopCV
```bash
.venv/bin/python -m job_scraper --source topcv --keyword "python" --pages 2 -o data/jobs.csv
```

### 2. Cào ITviec
```bash
.venv/bin/python -m job_scraper --source itviec --keyword "golang" --pages 2 -o data/jobs.csv
```

### 3. Cào URL bất kỳ (Generic)
```bash
.venv/bin/python -m job_scraper --source generic --url "https://careers.google.com/jobs/results/" -o data/jobs.csv
```

### 4. Chế độ nhanh (chỉ lấy listing, bỏ qua fetch trang con)
Thêm flag `--fast`:
```bash
.venv/bin/python -m job_scraper --source itviec --keyword "react" --pages 1 --fast -o data/jobs.csv
```

---

## Chạy Test

```bash
.venv/bin/python -m pytest tests/ -v
```
