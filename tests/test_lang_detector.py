from job_scraper.utils.lang_detector import is_english


def test_vietnamese_accent_detected_as_not_english() -> None:
    assert not is_english("Tuyển dụng Kỹ sư Python backend có kinh nghiệm")
    assert not is_english("Lập trình viên ReactJS tại Hà Nội")


def test_pure_english_detected() -> None:
    assert is_english("Senior Python Engineer with 3+ years experience in backend development")
    assert is_english("Fullstack Developer - We are looking for talented engineers")


def test_empty_is_not_english() -> None:
    assert not is_english("")
    assert not is_english(None)
