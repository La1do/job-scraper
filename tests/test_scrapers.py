from job_scraper.scrapers.generic import GenericScraper
from job_scraper.scrapers.itviec import ITViecScraper
from job_scraper.scrapers.topcv import TopCVScraper

TOPCV_SAMPLE = """
<div class="job-item-search-result">
  <h3 class="title">
    <a href="https://www.topcv.vn/viec-lam/senior-python-dev/123456.html">Senior Python Developer</a>
  </h3>
  <a class="company-name" href="/cong-ty/fpt">FPT Software</a>
  <label class="salary">20 - 35 triệu</label>
  <label class="address">Hà Nội</label>
  <label class="exp">3 năm</label>
</div>
"""

ITVIEC_SAMPLE = """
<div class="job-card">
  <h3><a href="/it-jobs/golang-backend-engineer-kms-123">Golang Backend Engineer</a></h3>
  <a href="/companies/kms-technology">KMS Technology</a>
  <div class="text-salary">1500 - 2500 USD</div>
  <div class="text-location">Ho Chi Minh</div>
  <a class="itag">Golang</a>
  <a class="itag">Remote</a>
</div>
"""

GENERIC_JSONLD_SAMPLE = """
<html>
<head>
<script type="application/ld+json">
{
  "@context": "https://schema.org/",
  "@type": "JobPosting",
  "title": "Lead Software Architect",
  "description": "We are seeking an experienced architect to lead our cloud platform.",
  "datePosted": "2026-10-01",
  "validThrough": "2026-11-01",
  "employmentType": "FULL_TIME",
  "hiringOrganization": { "@type": "Organization", "name": "VNG Corporation" },
  "jobLocation": {
    "@type": "Place",
    "address": { "addressLocality": "Ho Chi Minh City", "addressCountry": "VN" }
  },
  "baseSalary": {
    "@type": "MonetaryAmount",
    "currency": "USD",
    "value": { "minValue": 3000, "maxValue": 5000, "unitText": "MONTH" }
  },
  "url": "https://careers.vng.com.vn/job/123"
}
</script>
</head>
<body></body>
</html>
"""


def test_topcv_parse_listing() -> None:
    scraper = TopCVScraper()
    jobs = scraper.parse_listing(TOPCV_SAMPLE)
    assert len(jobs) == 1
    j = jobs[0]
    assert j.job_id == "topcv_123456"
    assert j.title == "Senior Python Developer"
    assert j.company_id == "FPT Software"
    assert j.min_salary == "20000000"
    assert j.max_salary == "35000000"
    assert j.currency == "VND"
    assert j.source_website == "TopCV"
    assert j.posting_domain == "topcv.vn"


def test_itviec_parse_listing() -> None:
    scraper = ITViecScraper()
    jobs = scraper.parse_listing(ITVIEC_SAMPLE)
    assert len(jobs) == 1
    j = jobs[0]
    assert j.job_id == "itviec_golang-backend-engineer-kms-123"
    assert j.title == "Golang Backend Engineer"
    assert j.company_id == "KMS Technology"
    assert j.min_salary == "1500"
    assert j.max_salary == "2500"
    assert j.currency == "USD"
    assert j.remote_allowed == "1"
    assert j.is_english == "True"
    assert j.source_website == "ITviec"


def test_generic_jsonld_parse() -> None:
    scraper = GenericScraper("https://careers.vng.com.vn/job/123")
    jobs = scraper.parse(GENERIC_JSONLD_SAMPLE, "https://careers.vng.com.vn/job/123")
    assert len(jobs) == 1
    j = jobs[0]
    assert j.title == "Lead Software Architect"
    assert j.company_id == "VNG Corporation"
    assert j.min_salary == "3000"
    assert j.max_salary == "5000"
    assert j.currency == "USD"
    assert j.pay_period == "MONTH"
    assert j.source_website == "Generic"
    assert j.is_english == "True"


CAREERVIET_SAMPLE = """
<div class="job-item" id="job-item-123ABC">
  <div class="figcaption">
    <h2>
      <a class="job_link" data-id="123ABC" href="/vi/tim-viec-lam/digital-marketing-specialist.html" title="Digital Marketing Specialist">
        Digital Marketing Specialist
      </a>
    </h2>
    <a class="company-name" title="Shopee Vietnam">Shopee Vietnam</a>
    <div class="salary"><p>Lương: 20 - 30 Triệu VND</p></div>
    <div class="location">Hồ Chí Minh</div>
    <div class="time">
      <time>15-11-2026</time>
      <time>14-10-2026</time>
    </div>
    <ul class="welfare"><li>Thưởng tháng 13</li><li>Bảo hiểm sức khỏe</li></ul>
  </div>
</div>
"""


def test_careerviet_parse_listing() -> None:
    from job_scraper.scrapers.careerviet import CareerVietScraper
    scraper = CareerVietScraper()
    jobs = scraper.parse_listing(CAREERVIET_SAMPLE)
    assert len(jobs) == 1
    j = jobs[0]
    assert j.job_id == "careerviet_123ABC"
    assert j.title == "Digital Marketing Specialist"
    assert j.company_id == "Shopee Vietnam"
    assert j.min_salary == "20000000"
    assert j.max_salary == "30000000"
    assert j.currency == "VND"
    assert j.location == "Hồ Chí Minh"
    assert j.expiry == "15-11-2026"
    assert j.listed_time == "14-10-2026"
    assert "Thưởng tháng 13" in j.skills_desc
    assert j.source_website == "CareerViet"
    assert j.is_english == "True"
