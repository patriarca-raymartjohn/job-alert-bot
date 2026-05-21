"""Central configuration.

Keywords can be overridden at runtime via the JOB_KEYWORDS env var
(comma-separated), so you can tweak them without editing code / redeploying.
"""
import os

# Each entry is a search term sent to a job platform's keyword search.
# Variants/synonyms are included so we don't miss differently-worded posts.
DEFAULT_KEYWORDS = [
    # Data / BI roles & skills
    "data analyst",
    "data engineer",
    "data analytics",
    "bi developer",
    "business intelligence",
    "power bi",
    "sql",
    "etl",
    "data entry",
    # QA / testing
    "tester",
    "qa",
    "qa engineer",
    "manual tester",
    "manual testing",
    "software qa testing",
    "quality assurance",
    # AI tools
    "ai tools",
    "claude",
    "claude code",
    "chatgpt",
    "codex",
    "base44",
]


def get_keywords() -> list[str]:
    raw = os.environ.get("JOB_KEYWORDS", "").strip()
    if raw:
        return [k.strip() for k in raw.split(",") if k.strip()]
    return DEFAULT_KEYWORDS


# Polite delay (seconds) between HTTP requests to the same site.
REQUEST_DELAY = float(os.environ.get("REQUEST_DELAY", "2"))

# HTTP request timeout (seconds).
REQUEST_TIMEOUT = float(os.environ.get("REQUEST_TIMEOUT", "20"))

# Where the dedup state lives (committed back to the repo by CI).
SEEN_FILE = os.environ.get("SEEN_FILE", "seen.json")

# Cap notifications per run so a first run / keyword change can't spam you
# with hundreds of messages. Older-than-this jobs are recorded as "seen"
# silently. Set to 0 for no cap.
MAX_NOTIFICATIONS_PER_RUN = int(os.environ.get("MAX_NOTIFICATIONS_PER_RUN", "20"))
