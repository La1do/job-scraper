"""Append job records to one CSV, dedup by job_id then job_posting_url.

Encoding is utf-8-sig so Excel opens Vietnamese text correctly.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from job_scraper.models import COLUMNS, JobRecord

log = logging.getLogger("job_scraper")


def _load_existing(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_records(path: str | Path, records: list[JobRecord]) -> tuple[int, int]:
    """Write records. Merges/updates records with better descriptions if already present."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    existing_rows = _load_existing(target)

    # Key by job_id or url
    by_key: dict[str, dict[str, str]] = {}
    row_keys: list[str] = []

    for r in existing_rows:
        key = r.get("job_id") or r.get("job_posting_url") or ""
        if key:
            by_key[key] = r
            row_keys.append(key)

    added = 0
    updated = 0
    skipped = 0

    for rec in records:
        new_row = rec.to_row()
        key = new_row.get("job_id") or new_row.get("job_posting_url") or ""
        if not key:
            continue

        if key in by_key:
            old_row = by_key[key]
            # If new row has richer description or skills_desc, update in place
            better_desc = len(new_row.get("description", "")) > len(old_row.get("description", ""))
            better_skills = len(new_row.get("skills_desc", "")) > len(old_row.get("skills_desc", ""))
            if better_desc or better_skills:
                # Merge: copy non-empty new fields into old
                for col in COLUMNS:
                    if new_row.get(col):
                        old_row[col] = new_row[col]
                updated += 1
            else:
                skipped += 1
        else:
            by_key[key] = new_row
            row_keys.append(key)
            added += 1

    try:
        with target.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore", lineterminator="\n")
            writer.writeheader()
            for key in row_keys:
                writer.writerow(by_key[key])
    except PermissionError:
        log.error("cannot write %s — file is open in another program (close Excel and retry)", target)
        raise

    log.info("csv %s: %d added, %d updated, %d skipped", target, added, updated, skipped)
    return added + updated, skipped
