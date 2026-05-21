"""OnlineJobs.ph scraper.

The search page is fully server-rendered (no JS needed). Results are
sorted newest-first and 30 per page, so for a frequent poll we only need
page 1 per keyword — anything new shows up at the top and dedup handles
the overlap between keywords.
"""
from __future__ import annotations

import re
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup

from .base import BaseScraper, Job

BASE_URL = "https://www.onlinejobs.ph"
SEARCH_URL = BASE_URL + "/jobseekers/jobsearch?jobkeyword={kw}"

# Trailing digits of /jobseekers/job/<slug>-<id> is the stable job id.
_ID_RE = re.compile(r"-(\d+)/?$|/(\d+)/?$")


class OnlineJobsPHScraper(BaseScraper):
    source = "onlinejobs.ph"

    def search(self, keyword: str) -> list[Job]:
        url = SEARCH_URL.format(kw=quote_plus(keyword))
        html = self._get(url).text
        return self._parse(html, keyword)

    def _parse(self, html: str, keyword: str) -> list[Job]:
        soup = BeautifulSoup(html, "html.parser")
        jobs: list[Job] = []

        for box in soup.select("div.jobpost-cat-box"):
            anchor = box.find_parent("a")
            if not anchor or not anchor.get("href"):
                continue
            href = anchor["href"]
            job_id = self._extract_id(href)
            if not job_id:
                continue

            # Title + job type. The type lives in a <span class="badge">
            # inside the <h4>; pull it out so the title stays clean.
            job_type = ""
            title = ""
            h4 = box.find("h4")
            if h4:
                badge = h4.find("span", class_="badge")
                if badge:
                    job_type = badge.get_text(strip=True)
                    badge.extract()
                title = h4.get_text(" ", strip=True)

            posted_at = ""
            p = box.find("p", attrs={"data-temp": True})
            if p:
                posted_at = p.get("data-temp", "").strip()

            salary = ""
            dd = box.find("dd")
            if dd:
                salary = dd.get_text(" ", strip=True)

            description = ""
            desc = box.find("div", class_="desc")
            if desc:
                description = desc.get_text(" ", strip=True)
                description = re.sub(r"\s*See More\s*$", "", description).strip()

            tags = [
                a.get_text(strip=True)
                for a in box.select("div.job-tag a.badge")
                if a.get_text(strip=True)
            ]

            jobs.append(
                Job(
                    source=self.source,
                    job_id=job_id,
                    title=title or "(untitled)",
                    url=urljoin(BASE_URL, href),
                    posted_at=posted_at,
                    salary=salary,
                    job_type=job_type,
                    description=description,
                    tags=tags,
                    matched_keywords=[keyword],
                )
            )

        return jobs

    @staticmethod
    def _extract_id(href: str) -> str:
        m = _ID_RE.search(href)
        if not m:
            return ""
        return m.group(1) or m.group(2) or ""
