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
| Practice app | `practice/` | Built-in tracker for running a consulting business: prospects, partners, conversations, engagements, time, invoices, expenses. Turned on with `apps = ["practice"]`. Our own company hub uses it. |
| Agents | `agents/` | Staff-like AI agents with roles and scheduled jobs (business development, social media, chief of staff). Their work lands in the practice Inbox for approval; they never send anything. `python -m kit.agents tick` from cron. |
| AI | `ai/` | "Ask AI" chat on every page, and home-page insights. See "The AI layer" below. |
| Admin | `manage.py` | Set up the database, add users, prove the AI login is read-only. |
| Ops | `../ops/`, `pgenv.py` | Backups (verified, off-site hook), restore test that fails loudly, cron, nginx, systemd. Scripts read `.env` safely and keep the password off the command line. |

## Run the demo locally
Needs Python 3.10+ and PostgreSQL 14+.
```bash
pip install -r requirements.txt
cp .env.example .env && chmod 600 .env    # fill in DATABASE_URL, SESSION_SECRET, AI_READER_PASSWORD
python clients/demo/generate.py           # make the fake systems' data
python -m kit.manage init-db
python -m kit.sync
python -m kit.manage create-user you@example.com "Your Name" --admin
uvicorn kit.hub.app:app --port 8000       # then open http://127.0.0.1:8000
python -m pytest -q tests                 # 48 tests (the AI and agent tests use a fake Claude, no key needed)
```
Set `SECURE_COOKIES=0` only when testing without HTTPS.

## Apps per install
`apps` in a client's `config.toml` picks what the hub shows: `["analytics"]` (default: the CRM/accounting pages,
for clients and the demo), `["practice"]` (the built-in tracker, for our own company hub), or both. The Ask AI chat
gets the matching tools.

## The AI layer
- **Ask AI** (button in the header of every page): questions in plain English. Claude answers by calling the
  hub's own metric functions (`ai/tools.py`), so its figures match the pages; each answer ends with "How I counted".
  All-branch users also get read-only SQL through the `ai_reader` login. Branch-limited users only get tools that
  respect their branches.
- **Insights** (home page): `python -m kit.ai.insights` from cron, 3 times a day. One call with structured output;
  each insight must contain a figure and link inside the hub, or it's dropped.
- **Safety:** read-only; nothing is sent anywhere; record text is treated as data, never instructions; links in
  answers are limited to hub paths and source-system links; answers render through `ai/render.py`, which escapes
  everything first.
- **Cost control:** one API key per feature (`ANTHROPIC_API_KEY_CHAT`, `ANTHROPIC_API_KEY_INSIGHTS`), monthly caps
  and a per-person daily question limit in `config.toml [ai]`, every call logged in `core.ai_usage` (shown on the
  Health page), at most 8 model calls per question.
- **Model:** `claude-opus-5-5` (set in `config.toml`), adaptive thinking, effort `medium` for chat and `high` for
  insights, prompt caching on, and server-side refusal fallback (`fallbacks: "default"`) on.
- **Keys:** the owner sets them on the server with `python -m kit.manage set-secret ANTHROPIC_API_KEY_CHAT`
  (typed hidden). Nobody else, including Claude, needs to see a key.

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
1. **AI, next steps:** measure real costs once the key is in; a read-only connection (MCP) so outside AI tools
   (Copilot, ChatGPT, Claude) can use the same governed data; AI-drafted monthly business review.
2. **Microsoft / Google sign-in**, replacing passwords (`hub/auth.py` is the only file that changes).
3. **Scheduled emails and alerts:** the weekly scorecard to inboxes, and alerts for failed syncs or backups.
4. **Real connectors:** Salesforce, HubSpot, QuickBooks Online.
5. **Pipeline movement** between any two dates, from history.
6. **Host the demo** online for prospects.
