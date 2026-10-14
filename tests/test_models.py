from job_scraper.models import COLUMNS, JobRecord


def test_columns_length() -> None:
    assert len(COLUMNS) == 30
    assert "source_website" in COLUMNS
    assert "is_english" in COLUMNS
    assert "scraped" in COLUMNS


def test_job_record_to_row_preserves_all_columns() -> None:
    rec = JobRecord(
        job_id="test_1",
        title="Python Engineer",
        company_id="acme",
        source_website="TopCV",
        is_english="True",
    )
    row = rec.to_row()
    assert list(row.keys()) == COLUMNS
    assert row["job_id"] == "test_1"
    assert row["title"] == "Python Engineer"
    assert row["source_website"] == "TopCV"
    assert row["is_english"] == "True"
    assert row["scraped"] != ""
