"""Append job records to one CSV, dedup by job_id then job_posting_url.

Encoding is utf-8-sig so Excel opens Vietnamese text correctly.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from job_scraper.models import COLUMNS, JobRecord

log = logging.getLogger("job_scraper")


def _load_seen(path: Path) -> tuple[set[str], set[str]]:
    ids: set[str] = set()
    urls: set[str] = set()
    if not path.exists() or path.stat().st_size == 0:
        return ids, urls
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if row.get("job_id"):
                ids.add(row["job_id"])
            if row.get("job_posting_url"):
                urls.add(row["job_posting_url"])
    return ids, urls


def write_records(path: str | Path, records: list[JobRecord]) -> tuple[int, int]:
    """Write records. Returns (added, skipped_duplicates)."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    seen_ids, seen_urls = _load_seen(target)
    new_file = not target.exists() or target.stat().st_size == 0

    added = 0
    skipped = 0
    try:
        with target.open("a", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore", lineterminator="\n")
            if new_file:
                writer.writeheader()
            for rec in records:
                row = rec.to_row()
                if (row["job_id"] and row["job_id"] in seen_ids) or (
                    row["job_posting_url"] and row["job_posting_url"] in seen_urls
                ):
                    skipped += 1
                    continue
                writer.writerow(row)
                if row["job_id"]:
                    seen_ids.add(row["job_id"])
                if row["job_posting_url"]:
                    seen_urls.add(row["job_posting_url"])
                added += 1
    except PermissionError:
        log.error("cannot write %s — file is open in another program (close Excel and retry)", target)
        raise
    log.info("csv %s: added %d, skipped %d duplicates", target, added, skipped)
    return added, skipped
