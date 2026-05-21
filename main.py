"""Orchestrator: scrape every enabled platform for every keyword,
notify about jobs we haven't seen, and persist the dedup state.

Run locally:   python main.py
Dry run:       DRY_RUN=1 python main.py   (scrape+filter, no Telegram, no state write)
"""
from __future__ import annotations

import os
import sys
import time
import traceback

import config
import state
from notify import TelegramConfigError, send_job
from scrapers import ENABLED_SCRAPERS
from scrapers.base import Job

DRY_RUN = os.environ.get("DRY_RUN", "").strip() in ("1", "true", "True")


def collect_jobs() -> list[Job]:
    """Scrape all platforms × keywords, deduping within this run by uid."""
    keywords = config.get_keywords()
    seen_this_run: set[str] = set()
    collected: list[Job] = []

    for scraper_cls in ENABLED_SCRAPERS:
        scraper = scraper_cls()
        for kw in keywords:
            try:
                results = scraper.search(kw)
            except Exception as exc:  # noqa: BLE001 - one bad keyword/site
                print(f"  ! {scraper_cls.source} '{kw}' failed: {exc}")
                continue
            new = 0
            for job in results:
                if job.uid in seen_this_run:
                    continue
                seen_this_run.add(job.uid)
                collected.append(job)
                new += 1
            print(f"  {scraper_cls.source} '{kw}': {len(results)} found, "
                  f"{new} unique this run")
    return collected


def main() -> int:
    print("=== Job Alert Bot ===")
    st = state.load_seen()

    jobs = collect_jobs()
    fresh = [j for j in jobs if not state.is_seen(st, j.uid)]
    print(f"Total unique scraped: {len(jobs)} | new (unseen): {len(fresh)}")

    if not fresh:
        print("Nothing new. Done.")
        return 0

    cap = config.MAX_NOTIFICATIONS_PER_RUN
    to_notify = fresh
    silent: list[Job] = []
    if cap and len(fresh) > cap:
        # Newest first so the cap keeps the most relevant alerts.
        to_notify = fresh[:cap]
        silent = fresh[cap:]
        print(f"Capping notifications at {cap}; "
              f"{len(silent)} older jobs recorded silently.")

    if DRY_RUN:
        print("\n[DRY_RUN] Would notify about:")
        for j in to_notify:
            print(f"  - [{j.matched_keyword}] {j.title} ({j.url})")
        return 0

    sent = 0
    try:
        for job in to_notify:
            if send_job(job):
                state.mark_seen(st, job.uid)
                sent += 1
                time.sleep(0.5)  # stay under Telegram's per-second limit
            else:
                # leave unseen so a later run retries it
                pass
    except TelegramConfigError as exc:
        print(f"FATAL: {exc}")
        return 2

    # Jobs intentionally not notified (over the cap) are still recorded
    # so they never trigger a late alert.
    for job in silent:
        state.mark_seen(st, job.uid)

    state.save_seen(st)
    print(f"Sent {sent} alert(s). State saved ({len(st['seen'])} known jobs).")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - never crash CI silently
        traceback.print_exc()
        sys.exit(1)
