# The kit

The reusable system we install for each client: data in one place, tools on top, AI later. It's plain Python and SQL with no build step, so it's easy to read and to hand over.

## What's in it
| Part | Files | What it does |
|---|---|---|
| Settings | `config.py`, `clients/<name>/config.toml`, `.env` | Business settings per client; secrets in a root-only `.env`. Missing settings stop start-up. |
| Database | `schema/*.sql` | Standard tables (`crm.*`, `acct.*`), kit tables (`core.*`), report views (`rpt.*`). Safe to re-run. |
| Connectors | `connectors/` | Each source system maps into the standard tables. Today: the demo CRM and demo accounting. |
| Sync | `sync.py` | Hourly copy. Upsert, then prune with a safety limit (refuses 0-row pulls and deletions over 10%). History tables only grow. Results go to `core.sync_state`. |
| Business rules | `metrics.py`, `cleanup.py` | Every number, computed once. Pages (and the AI, later) call these, so figures always match. |
| Hub | `hub/` | Web app: sign-in, home, scorecard, pipeline, win/loss, receivables, clean-up, health. |
| Admin | `manage.py` | Set up the database, add users, prove the AI login is read-only. |
| Ops | `../ops/` | Backups (verified, off-site hook), restore test, cron, nginx, systemd. |

## Run the demo locally
```bash
pip install -r requirements.txt
cp .env.example .env && chmod 600 .env    # fill in DATABASE_URL, SESSION_SECRET, AI_READER_PASSWORD
python clients/demo/generate.py           # make the fake systems' data
python -m kit.manage init-db
python -m kit.sync
python -m kit.manage create-user you@example.com "Your Name" --admin
uvicorn kit.hub.app:app --port 8000       # then open http://127.0.0.1:8000
python -m pytest -q tests                 # 23 tests
```
Set `SECURE_COOKIES=0` only when testing without HTTPS.

## Adding a real client
1. Copy `clients/demo/config.toml` to `clients/<client>/`. Set branches, goals, links to their CRM and accounting record pages, and sources.
2. Write or reuse a connector for each source system (`connectors/`). It maps their fields into the standard columns, with anything extra in `extra`.
3. Fill in `templates/rulebook-template.md` with them, then reproduce two or three of their existing reports to the cent before showing anything new.

The client's data, rulebook and config are theirs. The kit is ours and is licensed to them.

## Rules the code follows
- Percentages are weighted; missing values aren't zero; YTD compares the same dates.
- Every record shown links back to its source system; every number has a drill-down and a "how this is counted" note.
- Everything from data is HTML-escaped. CSV downloads block spreadsheet formula injection.
- The AI database login (`ai_reader`) can only SELECT from `rpt.*`, read-only, with a 15-second timeout.
- Chart.js is bundled (`hub/static/vendor`, v4.4.1, MIT), so no outside CDN is needed.

## Next up
1. **AI layer:** an "Ask" chat that calls the `metrics` functions as tools and ends answers with "How I counted"; daily insights; a secure read-only connection (MCP) for outside AI tools. Each feature gets its own key, spending cap and usage log.
2. **Microsoft / Google sign-in**, replacing passwords (`hub/auth.py` is the only file that changes).
3. **Scheduled emails and alerts:** the weekly scorecard to inboxes, and alerts for failed syncs or backups.
4. **Real connectors:** Salesforce, HubSpot, QuickBooks Online.
5. **Pipeline movement** between any two dates, from history.
6. **Host the demo** online for prospects.
