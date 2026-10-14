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
        self._pw = None
        self._browser = None
        self._context = None

    def close(self) -> None:
        if self._context:
            try:
                self._context.close()
            except Exception:
                pass
            self._context = None
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._pw:
            try:
                self._pw.stop()
            except Exception:
                pass
            self._pw = None

    def __enter__(self) -> BaseScraper:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

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

    def _ensure_browser(self) -> None:
        if self._browser and self._context:
            return
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=True)
        self._context = self._browser.new_context(user_agent=DEFAULT_HEADERS["User-Agent"])

    def _fetch_browser(self, url: str, params: dict | None = None) -> str | None:
        try:
            self._ensure_browser()
        except ImportError:
            log.warning("playwright not installed, cannot use browser fallback")
            return None
        except Exception as exc:
            log.error("failed to launch browser: %s", exc)
            return None

        target_url = url
        if params:
            from urllib.parse import urlencode
            sep = "&" if "?" in url else "?"
            target_url = f"{url}{sep}{urlencode(params)}"

        log.info("fetching via headless browser: %s", target_url)
        page = None
        try:
            page = self._context.new_page()
            page.goto(target_url, timeout=int(self.timeout * 1500), wait_until="domcontentloaded")
            content = page.content()
            return content
        except Exception as exc:
            log.error("browser fetch failed for %s: %s", target_url, exc)
            return None
        finally:
            if page:
                try:
                    page.close()
                except Exception:
                    pass

    @abstractmethod
    def scrape(self, keyword: str, pages: int, fast: bool) -> list[JobRecord]:
        """Return parsed job records. `keyword` may be empty for generic scrapers."""
