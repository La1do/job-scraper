#!/usr/bin/env bash
# Tự động cào và push dữ liệu mới lên GitHub
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

echo "=== [1/2] Bắt đầu cào dữ liệu ==="
.venv/bin/python scripts/crawl_500.py data/jobs.csv

echo "=== [2/2] Đẩy dữ liệu mới lên GitHub ==="
git add data/jobs.csv
if git diff --staged --quiet; then
  echo "Không có tin mới cần cập nhật."
else
  COUNT=$(wc -l < data/jobs.csv)
  git commit -m "data: update jobs dataset ($(date -u +"%Y-%m-%d %H:%M:%SZ"), total ${COUNT} rows)"
  git push origin main
  echo "Đã đẩy thành công lên GitHub!"
fi

echo ""
echo "Link tải CSV: https://raw.githubusercontent.com/La1do/job-scraper/main/data/jobs.csv"
