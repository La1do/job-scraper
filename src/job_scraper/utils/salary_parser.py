"""Parse Vietnamese and English salary strings into numeric fields.

Examples handled:
    "15 - 25 triệu"            -> min 15000000, max 25000000, VND, MONTH
    "Tới 40 triệu"             -> max 40000000, VND, MONTH
    "Từ 20 triệu"              -> min 20000000, VND, MONTH
    "$1,500 - $3,000"          -> min 1500, max 3000, USD, MONTH
    "1500 - 3000 USD"          -> min 1500, max 3000, USD, MONTH
    "20-30 triệu/tháng"        -> min 20000000, max 30000000, VND, MONTH
    "Thỏa thuận" / "Negotiable"-> empty
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_VI_ACCENT = re.compile(r"[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]", re.IGNORECASE)

_NUM = r"(\d+(?:[.,]\d+)*)"
_PREFIX = r"[$₫đ€£]?"
_RANGE_RE = re.compile(
    rf"{_PREFIX}\s*{_NUM}\s*[-–~]\s*{_PREFIX}\s*{_NUM}",
)
_SINGLE_RE = re.compile(rf"{_PREFIX}\s*{_NUM}")
_UP_TO_RE = re.compile(rf"(?:tới|upto|up to|dưới|under|max)\s*{_PREFIX}\s*{_NUM}", re.IGNORECASE)
_FROM_RE = re.compile(rf"(?:từ|from|trên|over|min)\s*{_PREFIX}\s*{_NUM}", re.IGNORECASE)


@dataclass
class Salary:
    min_salary: str = ""
    max_salary: str = ""
    med_salary: str = ""
    currency: str = ""
    pay_period: str = ""
    compensation_type: str = ""


def _to_float(token: str) -> float | None:
    cleaned = token.replace(",", "")
    # "15.5" is decimal; "15.000" (VN thousands) -> treat trailing 3 zeros as thousands only
    # when there are exactly 3 digits after the dot and no other dot.
    if re.fullmatch(r"\d+\.\d{3}", cleaned):
        cleaned = cleaned.replace(".", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _scale(value: float, text: str) -> float:
    low = text.lower()
    if "triệu" in low or "trieu" in low or "million" in low:
        return value * 1_000_000
    if re.search(r"\bk\b", low) or "nghìn" in low or "nghin" in low:
        return value * 1_000
    return value


def _currency(text: str) -> str:
    low = text.lower()
    if "$" in text or "usd" in low or "dollar" in low:
        return "USD"
    if "vnd" in low or "vnđ" in low or "đ" in text or "triệu" in low or "trieu" in low:
        return "VND"
    return ""


def _period(text: str) -> str:
    low = text.lower()
    if any(w in low for w in ("năm", "nam/", "/year", "per year", "annually", "/yr")):
        return "YEAR"
    if any(w in low for w in ("giờ", "gio", "/hour", "per hour", "/hr")):
        return "HOUR"
    if any(w in low for w in ("ngày", "ngay", "/day", "per day")):
        return "DAY"
    if any(w in low for w in ("tháng", "thang", "/month", "per month", "/mo")):
        return "MONTH"
    # default monthly for VND million ranges common in VN job boards
    if "triệu" in low or "trieu" in low:
        return "MONTH"
    return ""


def _fmt(value: float | None) -> str:
    if value is None:
        return ""
    if value == int(value):
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def parse_salary(text: str | None) -> Salary:
    result = Salary()
    if not text:
        return result
    raw = text.strip()
    low = raw.lower()
    if any(w in low for w in ("thỏa thuận", "thoa thuan", "negotiable", "competitive", "cạnh tranh")):
        return result

    result.currency = _currency(raw)
    result.pay_period = _period(raw)
    result.compensation_type = "BASE_SALARY" if result.currency else ""

    up_to = _UP_TO_RE.search(raw)
    from_ = _FROM_RE.search(raw)
    rng = _RANGE_RE.search(raw)

    if up_to and not rng:
        value = _scale(_to_float(up_to.group(1)) or 0, raw)
        result.max_salary = _fmt(value)
        return result
    if from_ and not rng:
        value = _scale(_to_float(from_.group(1)) or 0, raw)
        result.min_salary = _fmt(value)
        return result
    if rng:
        lo = _scale(_to_float(rng.group(1)) or 0, raw)
        hi = _scale(_to_float(rng.group(2)) or 0, raw)
        if lo > hi:
            lo, hi = hi, lo
        result.min_salary = _fmt(lo)
        result.max_salary = _fmt(hi)
        result.med_salary = _fmt((lo + hi) / 2)
        return result

    single = _SINGLE_RE.search(raw)
    if single:
        value = _scale(_to_float(single.group(1)) or 0, raw)
        result.min_salary = _fmt(value)
        result.max_salary = _fmt(value)
        result.med_salary = _fmt(value)
    return result
