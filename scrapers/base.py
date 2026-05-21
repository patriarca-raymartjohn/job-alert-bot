"""Common scraper interface + the Job model every scraper returns."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import requests

import config

# A realistic browser UA + headers. OnlineJobs.ph (and most sites with basic
# bot protection) return 403 to default library user-agents but 200 to this.
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


@dataclass
class Job:
    """Platform-agnostic job posting."""

    source: str          # e.g. "onlinejobs.ph"
    job_id: str          # unique within the source
    title: str
    url: str
    posted_at: str = ""  # raw string from the site, best-effort
    salary: str = ""
    job_type: str = ""   # Full Time / Part Time / ...
    description: str = ""
    tags: list[str] = field(default_factory=list)
    matched_keyword: str = ""

    @property
    def uid(self) -> str:
        """Globally-unique dedup key across all sources."""
        return f"{self.source}:{self.job_id}"


class BaseScraper(ABC):
    """Subclass this for each job platform."""

    #: short identifier stored on every Job and used in the dedup key
    source: str = "base"

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(BROWSER_HEADERS)

    def _get(self, url: str) -> requests.Response:
        """GET with shared headers, timeout, and a polite inter-request delay."""
        resp = self.session.get(url, timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
        time.sleep(config.REQUEST_DELAY)
        return resp

    @abstractmethod
    def search(self, keyword: str) -> list[Job]:
        """Return current (newest-first) job postings matching `keyword`."""
        raise NotImplementedError
