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
    """Scrape all platforms × keywords, deduping within this run by uid.

    A job surfaced by several keyword searches keeps ALL of them in
    matched_keywords. We then also flag any configured keyword that
    literally appears in the job's text, so each alert shows every
    keyword it actually matches (in config order).
    """
    keywords = config.get_keywords()
    by_uid: dict[str, Job] = {}
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
                existing = by_uid.get(job.uid)
                if existing is not None:
                    # Same job from another keyword search: merge the keyword.
                    for k in job.matched_keywords:
                        if k not in existing.matched_keywords:
                            existing.matched_keywords.append(k)
                    continue
                by_uid[job.uid] = job
                collected.append(job)
                new += 1
            print(f"  {scraper_cls.source} '{kw}': {len(results)} found, "
                  f"{new} new this run")

    # Enrich each job's matched list with any configured keyword that appears
    # in its title/description/tags, then order by the config keyword order.
    for job in collected:
        text = f"{job.title} {job.description} {' '.join(job.tags)}".lower()
        ordered = [
            kw for kw in keywords
            if kw in job.matched_keywords or kw.lower() in text
        ]
        for kw in job.matched_keywords:  # keep any non-config surfacing keyword
            if kw not in ordered:
                ordered.append(kw)
        job.matched_keywords = ordered

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

    # Throttle (don't drop): send at most `cap` this run; the rest stay
    # UNSEEN so the next run(s) deliver them. The backlog drains over time
    # and nothing matching is silently lost.
    cap = config.MAX_NOTIFICATIONS_PER_RUN
    to_notify = fresh[:cap] if cap else fresh
    deferred = len(fresh) - len(to_notify)
    if deferred:
        print(f"Throttling: sending {len(to_notify)} now; "
              f"{deferred} kept unseen for the next run(s).")

    if DRY_RUN:
        print("\n[DRY_RUN] Would notify about:")
        for j in to_notify:
            print(f"  - [{', '.join(j.matched_keywords)}] {j.title} ({j.url})")
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

    state.save_seen(st)
    deferred_note = f" ({deferred} queued for next run)" if deferred else ""
    print(f"Sent {sent} alert(s){deferred_note}. "
          f"State saved ({len(st['seen'])} known jobs).")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - never crash CI silently
        traceback.print_exc()
        sys.exit(1)
