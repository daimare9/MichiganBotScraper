# Michigan Bot Scraper 🏗️

Real-time email alerts for Michigan concrete construction contracts.

Monitors two public state procurement sources every 20 minutes and sends an
instant HTML email whenever a new bid matching your keywords is posted.

| Source | What it covers |
|--------|----------------|
| **MDOT Bid Letting** | Highway, road & bridge construction (concrete pavement, culverts, bridge decks…) |
| **SIGMA VSS** | All state-agency facility contracts (building slabs, foundations, masonry…) |

---

## Table of Contents

1. [Quick Start — Docker](#1-quick-start--docker)
2. [Gmail App Password Setup](#2-gmail-app-password-setup)
3. [Configuration](#3-configuration)
4. [Local Development (non-Docker)](#4-local-development-non-docker)
5. [GitHub Setup & Best Practices](#5-github-setup--best-practices)
6. [GitHub Actions (optional cloud run)](#6-github-actions-optional-cloud-run)
7. [How It Works](#7-how-it-works)
8. [Adding Keywords](#8-adding-keywords)
9. [Troubleshooting](#9-troubleshooting)
10. [Contributing](#10-contributing)

---

## 1. Quick Start — Docker

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- A Gmail account with an [App Password](#2-gmail-app-password-setup)

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/MichiganBotScraper.git
cd MichiganBotScraper

# 2. Create your .env from the template
cp .env.example .env

# 3. Edit .env with your credentials (see section 2 for Gmail setup)
#    Open .env in any text editor and fill in the four values.

# 4. Build and start the container
docker compose up --build -d

# 5. Watch the logs to confirm everything is working
docker compose logs -f
```

You should see output like:

```
2026-05-23 10:00:00 [INFO] src.main: Michigan Bot Scraper started
2026-05-23 10:00:00 [INFO] src.main: Poll interval : every 20 minutes
2026-05-23 10:00:00 [INFO] src.main: Keywords      : concrete, cement, pavement, ...
2026-05-23 10:00:01 [INFO] src.main: Scrape cycle starting…
2026-05-23 10:00:15 [INFO] MDOT: returned 3 matching contract(s)
2026-05-23 10:00:45 [INFO] SIGMA: returned 1 matching contract(s)
2026-05-23 10:00:45 [INFO] src.main: Sending email alert for 4 new contract(s)…
```

### Stop / restart

```bash
docker compose down        # stop and remove container
docker compose up -d       # restart (uses existing .env and data/)
docker compose restart     # restart without rebuilding
```

### Update to latest code

```bash
git pull
docker compose up --build -d
```

---

## 2. Gmail App Password Setup

Google requires an **App Password** (not your regular password) for SMTP access.

1. Enable 2-Factor Authentication on your Google account:
   [https://myaccount.google.com/security](https://myaccount.google.com/security)

2. Generate an App Password:
   [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
   - App name: `MichiganBotScraper` (or any label)
   - Copy the 16-character password shown

3. Add it to your `.env`:

   ```env
   GMAIL_USER=youraddress@gmail.com
   GMAIL_APP_PASSWORD=abcd efgh ijkl mnop   # paste exactly as shown (spaces OK)
   RECIPIENT_EMAIL=youraddress@gmail.com     # can be the same or different address
   ```

> **Tip:** You can send alerts to a different address than the sending account.
> Just set `RECIPIENT_EMAIL` to your preferred destination.

---

## 3. Configuration

All settings live in two places:

### `.env` — credentials & runtime settings

| Variable | Default | Description |
|----------|---------|-------------|
| `GMAIL_USER` | *(required)* | Gmail address used to send alerts |
| `GMAIL_APP_PASSWORD` | *(required)* | 16-char App Password from Google |
| `RECIPIENT_EMAIL` | *(required)* | Where alerts are delivered |
| `POLL_INTERVAL_MINUTES` | `20` | How often to scrape (minutes) |
| `DB_PATH` | `data/contracts.db` | Path to the SQLite dedup database |

### `config/keywords.yaml` — what to look for

```yaml
keywords:
  - concrete
  - cement
  - pavement
  - slab
  - foundation
  - flatwork
  - masonry
  - paving
  - rebar
  - precast
  - portland
  - curb and gutter
  - sidewalk
  - bridge deck
```

Edit this file and restart the container:

```bash
docker compose restart
```

Matching is **case-insensitive** and **substring-based** — `"pavement"` matches
`"HMA/PCC PAVEMENT RESTORATION"`.

---

## 4. Local Development (non-Docker)

### Requirements
- Python 3.12+
- Chromium (installed automatically by Playwright)

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/MichiganBotScraper.git
cd MichiganBotScraper

# Create a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Install Playwright's Chromium browser
playwright install chromium

# Set up your environment
cp .env.example .env
# Edit .env with your Gmail credentials

# Run the bot
python -m src.main
```

### Run tests

```bash
pytest
```

### Lint

```bash
ruff check src/ tests/
```

---

## 5. GitHub Setup & Best Practices

### Initial repository setup

```bash
cd MichiganBotScraper
git init
git add .
git commit -m "chore: initial commit — Michigan Bot Scraper"
git branch -M main

# Create a new repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/MichiganBotScraper.git
git push -u origin main
```

### Branch strategy

| Branch | Purpose |
|--------|---------|
| `main` | Stable, tested code — only merge via PR |
| `develop` | Integration branch for new features |
| `feat/xxx` | Feature branches (e.g. `feat/add-mideal-scraper`) |
| `fix/xxx` | Bug fixes |

```bash
# Start a new feature
git checkout -b feat/add-mideal-scraper

# When done, push and open a PR to main
git push -u origin feat/add-mideal-scraper
```

### Secrets — NEVER commit `.env`

The `.gitignore` already excludes `.env`.  
If you accidentally commit credentials, rotate them immediately and use
`git filter-repo` to purge history.

For team use or GitHub Actions, store secrets in:
**Settings → Secrets and variables → Actions**

| Secret name | Value |
|-------------|-------|
| `GMAIL_USER` | your Gmail address |
| `GMAIL_APP_PASSWORD` | your App Password |
| `RECIPIENT_EMAIL` | alert destination |

### Pull Request checklist

Before merging to `main`:

- [ ] `pytest` passes locally
- [ ] `ruff check` passes (no lint errors)
- [ ] `.env` is **not** included in the diff
- [ ] `data/` directory changes are **not** included
- [ ] You have tested a full scrape cycle manually

### Recommended GitHub repository settings

1. **Branch protection on `main`:**  
   Settings → Branches → Add rule → Require PR before merging, Require status checks

2. **Dependabot alerts:**  
   Settings → Security → Enable Dependabot alerts (keeps Playwright and requests patched)

3. **Topics (for discoverability):**  
   Add topics: `web-scraping`, `michigan`, `construction`, `procurement`, `python`, `playwright`

---

## 6. GitHub Actions (optional cloud run)

The repo includes `.github/workflows/scraper.yml` which can run the bot on a
schedule for free using GitHub's compute — **no server needed**.

### Enable it

1. Open `.github/workflows/scraper.yml`
2. Delete the line `if: false`
3. Add your secrets in **Settings → Secrets → Actions** (see table above)
4. Commit and push to `main`

GitHub will run a scrape every 30 minutes (minimum reliable GitHub Actions interval).

> **Note:** The SQLite database is persisted between runs using GitHub's cache.
> Caches expire after 7 days of inactivity. If the cache is evicted, you may
> get a one-time duplicate email for previously seen contracts.

### Manual trigger

You can trigger a scrape any time from:  
**Actions tab → "Scheduled Scrape" → Run workflow**

---

## 7. How It Works

```
┌─────────────────────────────────────────────────────────┐
│                   main.py (scheduler)                   │
│  Runs every POLL_INTERVAL_MINUTES using `schedule` lib  │
└──────────────────┬──────────────────────────────────────┘
                   │
         ┌─────────┴──────────┐
         ▼                    ▼
┌─────────────────┐  ┌─────────────────────────┐
│ MDOTLettingScraper│  │  SigmaVSSScraper        │
│ (Playwright)    │  │  (Playwright)            │
│                 │  │                          │
│ mdotjboss.state │  │  sigma.michigan.gov      │
│ .mi.us          │  │  /PRDVSS1X1/Advantage4   │
└────────┬────────┘  └──────────┬──────────────┘
         │                      │
         └──────────┬───────────┘
                    ▼
         ┌──────────────────────┐
         │  Keyword filter      │
         │  (config/keywords)   │
         └──────────┬───────────┘
                    ▼
         ┌──────────────────────┐
         │  ContractDatabase    │     Deduplication:
         │  (SQLite)            │ ◄── contracts already
         │                      │     emailed are skipped
         └──────────┬───────────┘
                    │  (only NEW contracts)
                    ▼
         ┌──────────────────────┐
         │  email_sender        │
         │  Gmail SMTP SSL      │ ──► Your inbox 📬
         └──────────────────────┘
```

### Deduplication

Each contract gets a stable `unique_key` = `"SOURCE:contract_id"`.  
Once a key is written to `data/contracts.db`, it is **never emailed again**,
even if the contract remains open on the site for weeks.

To re-trigger an alert for a specific contract (e.g. for testing):

```bash
# Find the key
sqlite3 data/contracts.db "SELECT unique_key FROM seen_contracts LIMIT 20;"

# Delete it so it gets emailed again next cycle
sqlite3 data/contracts.db "DELETE FROM seen_contracts WHERE unique_key = 'MDOT:26-1234';"
```

---

## 8. Adding Keywords

Edit `config/keywords.yaml`:

```yaml
keywords:
  - concrete
  - masonry
  - your-new-keyword   # ← add here
```

Then restart:

```bash
# Docker
docker compose restart

# Local
# Just restart: python -m src.main  (reads config fresh on startup)
```

### To broaden the search (catch more bids)

Add terms like: `earthwork`, `grading`, `storm sewer`, `drainage`,
`excavation`, `fill`, `compaction`

### To narrow the search (reduce noise)

Remove generic terms and keep only: `concrete`, `cement`, `portland`

---

## 9. Troubleshooting

### No emails arriving

1. Check Docker logs: `docker compose logs -f`
2. Verify Gmail App Password is correct (try re-generating it)
3. Confirm `RECIPIENT_EMAIL` is set correctly
4. Check Gmail's Spam folder
5. Try a manual SMTP test:

```python
import smtplib
with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
    s.login("you@gmail.com", "your-app-password")
    print("Login OK")
```

### "Missing required environment variables" error

Make sure `.env` exists in the project root and contains all three required variables.
The container reads `.env` via `env_file: .env` in `docker-compose.yml`.

### MDOT scraper returns 0 results

The MDOT site may have changed its HTML structure. Check:

```bash
docker compose logs | grep MDOT
```

If you see `"0 relevant letting date(s)"`, the sidebar date parser needs updating.
Open `src/scrapers/mdot_letting.py` and inspect `_collect_letting_links()`.

### SIGMA VSS scraper returns 0 results

The SIGMA VSS SPA may have updated its URL routing. Check:

```bash
docker compose logs | grep SIGMA
```

If you see `"could not reach solicitations page"`, try the direct URLs in
`SigmaVSSScraper._try_direct_url()` in your browser and update the list.

### Container keeps restarting

```bash
docker compose logs bot | tail -50
```

Common causes:
- Bad `.env` values (missing credentials)
- Port conflict (not applicable — this container doesn't expose ports)
- Out of disk space (`docker system prune` frees unused layers)

### Reset the dedup database (get all current contracts re-emailed)

```bash
docker compose down
rm data/contracts.db
docker compose up -d
```

---

## 10. Contributing

1. Fork the repo and create a feature branch from `develop`
2. Write tests for any new scraper or behaviour change
3. Ensure `pytest` and `ruff check` pass
4. Open a PR to `develop` — describe what changed and why
5. A maintainer will review and merge to `main`

### Adding a new scraper

1. Create `src/scrapers/my_source.py` inheriting from `BaseScraper`
2. Implement `scrape() -> list[Contract]` — never raise
3. Add it to the `scrapers` list in `src/main.py`
4. Add tests in `tests/test_my_source.py`
5. Document the source in this README

### Potential future scrapers

| Source | URL | Notes |
|--------|-----|-------|
| MiDEAL | michigan.gov/mideal | Local gov purchasing cooperative |
| SAM.gov | sam.gov | Federal contracts (MDOT federally funded projects) |
| BidNet | bidnet.com | Multi-state construction bid aggregator |
| DemandStar | demandstar.com | Local Michigan municipality bids |

---

## License

MIT — use freely, attribution appreciated.

---

*Built with Python 3.12 · Playwright · SQLite · Gmail SMTP*  
*Data sources: Michigan DTMB SIGMA VSS · MDOT Bid Letting*
