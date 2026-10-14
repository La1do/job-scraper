from job_scraper.utils.salary_parser import parse_salary


def test_vnd_range_millions() -> None:
    s = parse_salary("15 - 25 triệu")
    assert s.min_salary == "15000000"
    assert s.max_salary == "25000000"
    assert s.med_salary == "20000000"
    assert s.currency == "VND"
    assert s.pay_period == "MONTH"


def test_vnd_upto() -> None:
    s = parse_salary("Tới 40 triệu VND/tháng")
    assert s.max_salary == "40000000"
    assert s.min_salary == ""
    assert s.currency == "VND"
    assert s.pay_period == "MONTH"


def test_usd_range() -> None:
    s = parse_salary("$1,500 - $3,000")
    assert s.min_salary == "1500"
    assert s.max_salary == "3000"
    assert s.med_salary == "2250"
    assert s.currency == "USD"


def test_negotiable() -> None:
    s = parse_salary("Thỏa thuận")
    assert s.min_salary == ""
    assert s.max_salary == ""
    assert s.currency == ""
