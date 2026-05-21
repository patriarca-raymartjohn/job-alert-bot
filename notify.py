"""Telegram notifier.

Reads credentials from env vars (set as GitHub repo Secrets):
  TELEGRAM_BOT_TOKEN  - from @BotFather
  TELEGRAM_CHAT_ID    - your numeric chat id (see README step 2)
"""
from __future__ import annotations

import html
import os
import time

import requests

from scrapers.base import Job

API = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramConfigError(RuntimeError):
    pass


def _creds() -> tuple[str, str]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        raise TelegramConfigError(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set."
        )
    return token, chat_id


def format_job(job: Job) -> str:
    e = html.escape
    lines = [f"\U0001f4bc <b>{e(job.title)}</b>"]
    meta = []
    if job.job_type:
        meta.append(e(job.job_type))
    if job.salary:
        meta.append(e(job.salary))
    if meta:
        lines.append(" • ".join(meta))
    if job.posted_at:
        lines.append(f"\U0001f553 Posted: {e(job.posted_at)}")
    if job.tags:
        lines.append("\U0001f3f7 " + ", ".join(e(t) for t in job.tags))
    if job.description:
        desc = job.description[:300]
        if len(job.description) > 300:
            desc += "…"
        lines.append(e(desc))
    lines.append(f"\U0001f517 <a href=\"{e(job.url)}\">View job</a>")
    matched = ", ".join(job.matched_keywords) if job.matched_keywords else "—"
    lines.append(f"<i>{e(job.source)} — matched: {e(matched)}</i>")
    return "\n".join(lines)


def send_job(job: Job) -> bool:
    """Send one job. Returns True on success. Handles 429 rate limits."""
    token, chat_id = _creds()
    payload = {
        "chat_id": chat_id,
        "text": format_job(job),
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    for attempt in range(3):
        resp = requests.post(API.format(token=token), data=payload, timeout=20)
        if resp.status_code == 200:
            return True
        if resp.status_code == 429:
            retry_after = resp.json().get("parameters", {}).get("retry_after", 5)
            time.sleep(retry_after + 1)
            continue
        # Other error: report once and give up on this job.
        print(f"  ! Telegram error {resp.status_code}: {resp.text[:200]}")
        return False
    return False
