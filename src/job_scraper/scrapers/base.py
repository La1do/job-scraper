"""Base scraper: shared HTTP client and interface."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import httpx

from job_scraper.models import JobRecord

log = logging.getLogger("job_scraper")

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class BaseScraper(ABC):
    source_website: str = ""
    posting_domain: str = ""

    def __init__(self, timeout: float = 20.0, retries: int = 3) -> None:
        self.timeout = timeout
        self.retries = retries

    def fetch(self, url: str, params: dict | None = None, allow_browser_fallback: bool = True) -> str | None:
        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                with httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=self.timeout) as client:
                    resp = client.get(url, params=params)
                if resp.status_code == 403:
                    log.warning("403 from %s (anti-bot)", url)
                    if allow_browser_fallback:
                        return self._fetch_browser(url, params)
                    return None
                resp.raise_for_status()
                return resp.text
            except httpx.HTTPError as exc:
                last_error = exc
                log.warning("fetch attempt %d/%d failed for %s: %s", attempt, self.retries, url, exc)
        if allow_browser_fallback:
            return self._fetch_browser(url, params)
        log.error("giving up on %s: %s", url, last_error)
        return None

    def _fetch_browser(self, url: str, params: dict | None = None) -> str | None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            log.warning("playwright not installed, cannot use browser fallback")
            return None

        target_url = url
        if params:
            from urllib.parse import urlencode
            sep = "&" if "?" in url else "?"
            target_url = f"{url}{sep}{urlencode(params)}"

        log.info("launching headless browser for %s", target_url)
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(user_agent=DEFAULT_HEADERS["User-Agent"])
                page.goto(target_url, timeout=int(self.timeout * 1500), wait_until="domcontentloaded")
                content = page.content()
                browser.close()
                return content
        except Exception as exc:
            log.error("browser fetch failed for %s: %s", target_url, exc)
            return None

    @abstractmethod
    def scrape(self, keyword: str, pages: int, fast: bool) -> list[JobRecord]:
        """Return parsed job records. `keyword` may be empty for generic scrapers."""
