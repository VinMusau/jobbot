# JobBot

Daily digest of entry/mid-level software development and engineering roles — Kenya (full-time/hybrid) and worldwide remote — scored by an LLM and emailed to me.

## How It Works

```text
GitHub Actions (daily 06:00 UTC / 09:00 EAT)
        │
        ▼
Scrape sources ──► dedupe by URL hash
        │
        ▼
Regex pre-filter (drops senior/non-software)
        │
        ▼
Groq LLM scoring (0–10, batched 8 jobs/call)
        │
        ▼
Gmail SMTP digest (jobs scoring ≥ MIN_SCORE)
```

## Sources

| Source         | Type        | Region |
| -------------- | ----------- | ------ |
| Remotive       | JSON API    | Remote |
| RemoteOK       | JSON API    | Remote |
| Jobicy         | JSON API    | Remote |
| BrighterMonday | HTML scrape | Kenya  |
| JobWebKenya    | HTML scrape | Kenya  |
| MyJobMag Kenya | HTML scrape | Kenya  |

> **Disabled sources**
>
> * **Fuzu** — Cloudflare blocks non-browser requests.
> * **Adzuna** — Kenya endpoint requires separate approval.

## Files

| File           | Purpose                                    |
| -------------- | ------------------------------------------ |
| `main.py`      | Orchestrator — run this                    |
| `sources.py`   | All scrapers, returns normalized job dicts |
| `ai_filter.py` | Regex pre-filter + Groq scoring            |
| `emailer.py`   | Gmail SMTP digest sender                   |
| `db.py`        | SQLite storage + dedupe                    |
| `jobs.db`      | Local DB (gitignored, cached in Actions)   |

## Setup

1. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   ```

2. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and fill in the required variables:

   ```bash
   cp .env.example .env
   ```

   | Variable             | Description                                      |
   | -------------------- | ------------------------------------------------ |
   | `GROQ_API_KEY`       | [Groq API key](https://console.groq.com)         |
   | `GMAIL_USER`         | Full Gmail address                               |
   | `GMAIL_APP_PASSWORD` | 16-character app password (not account password) |
   | `TO_EMAIL`           | Email address where the digest is sent           |
   | `GROQ_MODEL`         | Defaults to `openai/gpt-oss-120b`                |
   | `MIN_SCORE`          | Email threshold, default `7`                     |

4. Run the application:

   ```bash
   python main.py
   ```

### Gmail App Password

Gmail requires 2FA to be enabled before an app password can be generated.

Generate one at:

[Google App Passwords](https://myaccount.google.com/apppasswords)

> **Important:** Do not use your regular Gmail account password. SMTP will reject it.

## Deploy

JobBot runs on GitHub Actions using:

```text
.github/workflows/digest.yml
```

Add the same environment variables as **repository secrets**.

You can trigger the workflow manually from the **Actions** tab to test it.

## Tuning

* **Too few emails?** Lower `MIN_SCORE` to `6`, or loosen `SOFTWARE_HINTS` in `ai_filter.py`.
* **Too many junk roles?** Raise `MIN_SCORE` to `8`, or tighten `SENIOR_BLOCK`.
* **A source returns 0 for days?** Selectors broke. Dump the page HTML and re-inspect.
* **Duplicate emails?** `actions/cache` isn't restoring `jobs.db` — migrate to Postgres.

## Roadmap

* [ ] Migrate to Postgres (Supabase) — kills the Actions cache fragility
* [ ] Web UI (FastAPI + Jinja2 + HTMX) to browse/filter jobs
* [ ] CV upload + per-job match scoring
* [ ] Application tracking (applied → interview → offer funnel)

## Notes

* Never commit `.env` or `jobs.db`.
* Groq free tier: ~30 requests/min, ~1k requests/day. Current usage ~5 requests/run.
* `jobwebkenya` uses `/job-tag/` paths, not `/category/` — don't guess URLs; dump the homepage first.
