# Job Alert Bot

Scrapes [OnlineJobs.ph](https://www.onlinejobs.ph) every ~15 minutes and sends you a
**Telegram** message for every new job matching your keywords (SQL, Power BI, tester,
data analyst, data engineer, BI developer, and related roles).

Runs entirely on **GitHub Actions** — $0, no server. Dedup state lives in `seen.json`,
which the workflow commits back to the repo after each run, so you never get the same
job twice.

> Architecture is **pluggable**: each platform is one module under `scrapers/`.
> OnlineJobs.ph is implemented; Indeed / Glassdoor / etc. can be added later by
> dropping in a new scraper and registering it in `scrapers/__init__.py`.

---

## Setup (one time, ~5 minutes)

### 1. Create your Telegram bot
1. In Telegram, message [@BotFather](https://t.me/BotFather).
2. Send `/newbot`, follow the prompts, and copy the **bot token** it gives you
   (looks like `123456789:AAH...`).
3. Open your new bot and send it any message (e.g. `hi`) — this is required so the
   bot is allowed to message you back.

### 2. Get your chat ID
With the token from step 1, open this URL in a browser (replace `<TOKEN>`):

```
https://api.telegram.org/bot<TOKEN>/getUpdates
```

Find `"chat":{"id":<NUMBER>` in the JSON — that `<NUMBER>` is your **chat ID**.

### 3. Create the repo & add secrets
1. Push this folder to a new GitHub repo.
2. In the repo: **Settings → Secrets and variables → Actions → New repository secret**,
   and add both:
   - `TELEGRAM_BOT_TOKEN` → the token from step 1
   - `TELEGRAM_CHAT_ID` → the number from step 2
3. (Optional) To change keywords without editing code, add a repo **Variable**
   (same screen, "Variables" tab) named `JOB_KEYWORDS`, comma-separated, e.g.
   `sql, power bi, data analyst, etl`.

That's it. The workflow runs automatically every ~15 min. You can also trigger it
manually: **Actions → Job Alert Bot → Run workflow**.

---

## Run / test locally

```powershell
pip install -r requirements.txt

# Dry run — scrapes + filters and prints matches, sends nothing, writes nothing:
$env:DRY_RUN = "1"; python main.py

# Real run locally (sends Telegram, updates seen.json):
$env:DRY_RUN = ""
$env:TELEGRAM_BOT_TOKEN = "..."
$env:TELEGRAM_CHAT_ID = "..."
python main.py
```

---

## How it works

```
GitHub Actions cron (*/15)
        │
        ▼
   main.py ──► scrapers/ (OnlineJobs.ph: 1 search request per keyword, page 1)
        │            │
        │            ▼
        │      filter + dedup within run (by source:job_id)
        │            │
        ▼            ▼
   seen.json ◄── skip already-notified ──► Telegram (new jobs only)
   (committed back to repo)
```

## Tuning

All knobs are env vars (see [`config.py`](config.py)):

| Var | Default | Meaning |
|---|---|---|
| `JOB_KEYWORDS` | built-in list | Comma-separated search terms |
| `MAX_NOTIFICATIONS_PER_RUN` | `20` | Cap alerts/run (first run won't spam you; older jobs recorded silently) |
| `REQUEST_DELAY` | `2` | Seconds between requests (be polite) |
| `REQUEST_TIMEOUT` | `20` | HTTP timeout (seconds) |

## Notes & limits

- **GitHub cron drift:** scheduled runs are best-effort and can be 20–40 min late
  under load. Dedup makes this harmless — you still get every job, just not on an
  exact 15-min beat.
- **OnlineJobs.ph:** public job-seeker pages are scraped with a browser User-Agent
  (the site 403s default bots). Full employer contact details require a logged-in
  OnlineJobs.ph account and are intentionally **not** scraped here.
- **First run:** with an empty `seen.json`, the newest 20 matches are sent and the
  rest are silently marked seen, so you aren't flooded.
