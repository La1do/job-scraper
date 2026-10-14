import csv
from pathlib import Path

from job_scraper.models import COLUMNS, JobRecord
from job_scraper.storage.csv_writer import write_records


def test_csv_creation_and_deduplication(tmp_path: Path) -> None:
    out = tmp_path / "jobs.csv"
    r1 = JobRecord(job_id="job_1", title="Dev 1", job_posting_url="https://site.com/1")
    r2 = JobRecord(job_id="job_2", title="Dev 2", job_posting_url="https://site.com/2")
    r3 = JobRecord(job_id="job_1", title="Dev 1 duplicate", job_posting_url="https://site.com/1")

    # First write
    added, skipped = write_records(out, [r1, r2, r3])
    assert added == 2
    assert skipped == 1

    # Check BOM signature
    raw = out.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")

    # Second write: append with existing id and new id
    r4 = JobRecord(job_id="job_3", title="Dev 3", job_posting_url="https://site.com/3")
    added2, skipped2 = write_records(out, [r2, r4])
    assert added2 == 1
    assert skipped2 == 1

    # Verify total rows in CSV
    with out.open("r", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 3
    assert [r["job_id"] for r in rows] == ["job_1", "job_2", "job_3"]
    assert list(rows[0].keys()) == COLUMNS
