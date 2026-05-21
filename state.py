"""Dedup state: which job UIDs we've already notified about.

Stored as a small JSON file that CI commits back to the repo after each
run, so the bot remembers across runs with zero external services.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import config


def load_seen() -> dict:
    path = config.SEEN_FILE
    if not os.path.exists(path):
        return {"seen": {}}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if "seen" not in data or not isinstance(data["seen"], dict):
            return {"seen": {}}
        return data
    except (json.JSONDecodeError, OSError):
        # Corrupt/unreadable state: start fresh rather than crash the run.
        return {"seen": {}}


def is_seen(state: dict, uid: str) -> bool:
    return uid in state["seen"]


def mark_seen(state: dict, uid: str) -> None:
    state["seen"][uid] = datetime.now(timezone.utc).isoformat()


def save_seen(state: dict) -> None:
    tmp = config.SEEN_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, sort_keys=True)
    os.replace(tmp, config.SEEN_FILE)
