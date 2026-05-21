"""Pluggable job-platform scrapers.

To add a new platform (Indeed, Glassdoor, ...):
  1. Create scrapers/<platform>.py with a class subclassing BaseScraper.
  2. Implement `search(keyword) -> list[Job]`.
  3. Register it in ENABLED_SCRAPERS below.
"""
from .base import BaseScraper, Job
from .onlinejobs_ph import OnlineJobsPHScraper

# Order here = order jobs are fetched. Add future platforms to this list.
ENABLED_SCRAPERS: list[type[BaseScraper]] = [
    OnlineJobsPHScraper,
    # IndeedScraper,      # TODO: future
    # GlassdoorScraper,   # TODO: future
]

__all__ = ["BaseScraper", "Job", "ENABLED_SCRAPERS"]
