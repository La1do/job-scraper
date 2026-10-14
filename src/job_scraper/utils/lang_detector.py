"""Detect whether a job posting is written in English.

Rule:
- Any Vietnamese diacritic in the text -> not English.
- Otherwise, if at least one common English job-posting token is present -> English.
- Empty text -> not English.
"""

from __future__ import annotations

import re

_VI_DIACRITIC = re.compile(
    r"[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩị"
    r"òóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]",
    re.IGNORECASE,
)

_EN_TOKENS = re.compile(
    r"\b(the|and|for|with|you|our|we|are|looking|requirements|"
    r"experience|responsibilities|skills|about|join|team|role|"
    r"position|developer|engineer|salary|benefits|apply|"
    r"marketing|specialist|manager|executive|officer|lead|"
    r"analyst|consultant|intern|internship|designer|director)\b",
    re.IGNORECASE,
)


def is_english(*parts: str | None) -> bool:
    text = " ".join(p for p in parts if p).strip()
    if not text:
        return False
    if _VI_DIACRITIC.search(text):
        return False
    return _EN_TOKENS.search(text) is not None
