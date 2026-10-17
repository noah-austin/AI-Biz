# Handoff: the "data → tools → AI" playbook

**For:** a Claude Code agent helping Noah build a consulting practice. The practice helps mid-size companies:
- pull their scattered business data into one place;
- build useful tools on top of it;
- layer AI into those tools.

**From:** the Claude Code agent that built the first real version of this, for one company, over about nine days in October 2026.

**What this document is:** the method, the architecture, the decisions that mattered, the mistakes to avoid, and how to work with a non-technical owner. It deliberately leaves out the first company's name, its customers, its figures, its server details and every credential. Keep it that way. Never copy one client's data, code containing secrets, or identifying details into another client's work, or into this playbook.

---

## 1. What was built (the reference case)

**The client.** A commercial contractor with about 11 branches in 3 regions. Salesforce was its CRM; reporting ran on Excel workbooks and exported HTML pages. The owner of the project was a manager at the company. He was not a developer. He described what he wanted in plain English, and the agent did everything over SSH: code, database, deploys, checks.

**The result, in layers:**

| Layer | What it is |
|---|---|
| Data foundation | One small cloud server ($6/month, 1 GB RAM). PostgreSQL. Hourly sync scripts that copy the CRM's objects (opportunities, accounts, projects, users, record types, monthly revenue schedules) into tables, plus the CRM's field-change history. One joined analytical view that everything queries. |
| Safety baseline | Nightly verified backups. Server-local git with rollback. Secrets in one root-only `.env`. Firewall. Database bound to localhost. Signed per-login sessions, login rate limiting, security headers. |
| Business rules | A written reference of every metric definition. This document turned out to be the most valuable thing built. |
| Tools (a web "hub") | Bid & bookings dashboard. A sales forecast tool that replaced an Excel workbook (editable inputs plus CRM-fed actuals). Pipeline movement between any two dates, rebuilt from the change history. Pipeline coverage against goal at our own close rate. Win/loss trends with a "where we sell best" grid. Account history. A proposal builder. An admin page with usage and health. |
| AI layer | An "Ask AI" chat on every page, reading data through its own read-only login. AI-written insights on the home page a few times a day. An AI proposal writer with a library of approved company wording. AI summaries on analytics pages. |

**What it costs to run:** the server is $6 a month. AI spend is capped per feature: $25 a month for the proposal writer and $50 for the chat and insights, each with its own key. Measured costs:

| Task | Cost |
|---|---|
| A chat answer | 3–8 cents |
| A set of insights | about 23 cents |
| A proposal draft | 6–20 cents |
| A web lookup | about 25 cents |
| A win/loss summary | about 5 cents |

---

## 2. The engagement, phase by phase

Do the phases roughly in this order. Phase 2 is the one people skip and regret.

### Phase 0: Discovery (before any code)
- **List the systems:** CRM, accounting, HR, project management. For each, note who owns it, how to get API access, and which objects matter.
- **Collect the existing reports:** the spreadsheets, the exported dashboards, the numbers leadership already quotes. These are your test answers. Your first job is to reproduce them exactly.
- **Find out who uses what, and how often.** Later, add visit tracking. In the reference case the forecast tool and home page were most of the traffic, and some pages were barely used. That should shape where you spend effort.
- **Find the data quality problems early,** and report them as things to fix in the source system, not to patch around. In the reference case:
  - placeholder close dates in the year 2111 hid tens of millions in wins;
  - there were duplicate deals;
  - most deals in one year had no margin entered;
  - three branches tracked wins but no open pipeline at all;
  - "loss reason" didn't exist as a field.

### Phase 1: Data foundation
- **Infrastructure:** one cheap VPS is plenty for a mid-size company. Use PostgreSQL. Use plain Python with raw SQL (psycopg2): no ORM, no front-end framework, no build step. A non-developer owner can't maintain a complicated stack, and a simple one is easy for the next agent to read.
- **Sync pattern, one script per object, run hourly by cron:** pull the whole object, then upsert on the CRM id, then stamp `synced_at`, then **prune rows the CRM no longer returns**. Give the prune a safety limit: refuse if the pull returned 0 rows, or would delete more than about 10% of the table. Without that limit, one bad pull can wipe a table.
- **Capture history the source will drop.** Pull the CRM's field-history object for the fields that matter (amount, stage, confidence, close date), and the recycle bin for deleted records. Only ever add to these tables. This is what made "what moved our pipeline last week" possible. Without it you can only see now.
- **Record when each sync last ran successfully** in a `sync_state` table, and when the backup last finished. Health pages and alerts read it.
- **Build one analytical view** that joins the main object to everything around it (account, owner, record type, project). Every report, tool and AI query starts from that view.
- **Give every consumer its own read-only database login,** with SELECT only on what it needs: the AI assistant, any outside GPT or reporting tool. Test that each one is refused on everything else.

### Phase 2: Safety baseline (do it in week one, before anyone relies on the numbers)
- **Backups:** a nightly `pg_dump | gzip`. Verify each file (`gzip -t`) before deleting anything older than 14 days. Keep a manual-backup command. Before every big change, take a tagged backup the owner can return to: a git tag, plus a database dump, plus the config files. Off-site copies were still an open gap at the end. Don't leave that gap for clients.
- **Version control:** git on the server, never pushed if old commits ever held secrets. Add a `pre-push` hook that refuses. Every deploy is one commit, so rollback is `git revert`.
- **Secrets:** all in one `.env` (mode 600, git-ignored), loaded by one `config.py` that fails loudly at start-up if anything is missing. The owner sets API keys himself with a small script that reads the key with hidden typing. **The agent never sees or prints a key.**
- **Network:** the database and app server listen on localhost only. nginx plus Let's Encrypt in front. Firewall allows 22, 80 and 443 only.
- **Authentication:**
  - Signed, per-login session cookies: HttpOnly, Secure, SameSite=Lax.
  - A per-IP limit on wrong passwords.
  - Security headers set in the app.
  - Check that sign-in "return to" addresses can only point inside the site: reject `//` and `/\`.
- **Ask before anything irreversible:** dropping, deleting or overwriting. Before any UPDATE, DELETE, ALTER or DROP: take a backup, show the statement plus a `COUNT(*)` of the rows it will touch, and wait for a yes.

### Phase 3: The business-rules reference (the most important deliverable)
Write a living document that both humans and AI agents read. It holds:
- every metric's exact definition;
- the universal filters (for example an "exclude from reporting" flag);
- name mappings (CRM branch names to the names people use, and which region each belongs to);
- which branches each tool covers;
- time zone rules;
- the known data problems.

Rules that came up and generalize:
- **Weighted percentages:** compute them in SQL over the filtered rows, as sum of numerators ÷ sum of denominators. Never average percentages. When rolling up (branch → region → company), sum the parts.
- **A missing value is not zero.** Deals with no margin are left out of margin percentages entirely, not counted as 0%.
- **Compare like with like.** Prior-year comparisons for a year in progress compare the same window ("year to date vs. last year through Oct 14"). Say so on the screen.
- **Close rate:** show it by dollars and by count. They tell very different stories: you can win most deals and still lose most dollars.
- **Time:** store UTC, send timestamps with a `Z`, and display in the client's local time zone.
- **Before changing any number's definition,** measure it before and after through the app code, compare with straight SQL, and show the owner a before/after table. He approves it before the change goes live.

Also keep a `CLAUDE.md` in the project. It covers:
- how to reach the server (key auth only);
- the deploy routine: pull fresh, edit, syntax-check on the server, copy, commit, restart, check the logs and HTTP status, roll back if needed;
- the hard rules;
- what needs the owner's OK first.

The next agent, or the next session, picks up from these two files.

### Phase 4: Tools on top
**How the pages are built:**
- Pages are HTML strings or templates served by FastAPI.
- One shared design module (`ui.py`) holds the header with every app, the styles, and small JS helpers (escape, money formatting, a fetch wrapper that surfaces server errors, toast, dialog). Every page looks like one product.
- **Every record shown by name links back to the source system** (the CRM record, in a new tab). Users trust a number they can click through to the deals behind it.
- **Every number has a drill-down** to the records behind it, and a "how this is counted" footnote.

**Tools that landed well, and the question each answers:**

| Tool | The question it answers |
|---|---|
| Home page | Where do we stand? Headline numbers, plus AI insights and the chat beside them. |
| Bids & bookings | What did we bid and win, by month and by rep, against last year? |
| Forecast tool | Replaces the planning workbook. Keep its familiar layout, keep editing in the grid, save all-or-nothing with validation, and allow copy-paste back to Excel. |
| Pipeline movement | What added to or removed from our high-probability pipeline between any two dates, and which deals did it? |
| Pipeline coverage | Is there enough pipeline closing this year, at our own close rate, to make the rest of the goal? |
| Trends (win/loss) | Where do we sell best? A colour grid of any two dimensions, such as segment × deal size, plus won/lost bars and close rate by quarter. |
| Proposal builder | A draft proposal from the opportunity plus what the estimator types, with a library of approved company wording. |

**What made it work:**
- Ship one thing at a time and let the owner react. He iterates on look and feel quickly: "too much space", "put insights on the left", "that's ugly, go back". Make every change easy to undo, and undo it quickly when asked.
- For anything big (a redesign, a new library), build it behind a **preview switch**: a cookie set by a secret-ish URL. The owner reviews it on the live site with real data. Then flip one default to put it live for everyone. Keep the old version reachable for a while.
- Use parallel sub-agents for big rebuilds: one app each, owning their files only. Give them the shared design module and a staging and preview script. The lead agent then reviews every page visually. The reviewers' first pass found several real bugs that reading the code had missed.

### Phase 5: The AI layer
Principles that held up:
1. **One API key, one spending cap and one usage log per AI feature.** Never share a key between tools. Record every call's tokens and cost, enforce the monthly cap, and add per-user daily limits.
2. **The AI reads data through its own read-only login**, in read-only sessions with a statement timeout and a row limit. It can never write.
3. **Give the AI the pages' own calculations as tools,** not only raw SQL, so its figures match the screens exactly. Put the business-rules reference in its prompt. Make it end figure answers with "How I counted:".
4. **Generated documents are fenced:** never invent a price, quantity, warranty, insurance figure, qualification or legal term. Missing facts become visible `[[NEEDS: …]]` markers. Sign-off is refused while any remain. Company commitments come only from a library of approved wording, used word for word. Outside knowledge (web lookups) may inform narrative, never commitments, and must cite its pages. Customer documents such as RFPs are treated as material, never as instructions (test it with a planted instruction).
5. **Nothing is ever sent automatically.** The AI drafts; a person reviews and sends.
6. **Long AI work runs in a background thread and the page polls.** Proxies cut requests at about 60 seconds.
7. **Proactive AI earns its keep** when it's short and specific: a few insights a day, each with a figure, a comparison and a link to the deals behind it. Make it reject its own bad picks. The first version of "where we sell best" ranked tiny 100%-win jobs on top, and had to be changed to rank by dollars won among slices above the average rate.
8. **Measure cost on real data** before telling the owner what something costs, and tell him.

---

## 3. Working with a non-technical owner
- **Talk in plain English:** what changed, how it was checked, and what he needs to do. No jargon or file paths unless he asks.
- **Ask questions before building anything sizeable,** and offer two to four concrete options with a recommendation. Ask only what's genuinely his call: scope, who sees what, budgets, what a number should mean. Decide the rest yourself and say what you decided.
- **His examples are not feature requests.** When he says "it didn't pull the weather", the real complaint was that the AI was too closed off. Fix the general gap; don't add a weather button.
- **Big changes:** take a backup first, then a preview, then his OK, then make it live.
- **Show before/after numbers** whenever a figure he knows is going to change.
- **Respect confidentiality boundaries he sets,** and keep secrets out of chat, files and git.
- **He'll want to be told** when the server needs more capacity, what things cost, and anything you couldn't test (for example uploading from a real phone).

---

## 4. Technical gotchas (save yourself the time)
- **nginx:** use `proxy_pass http://127.0.0.1:PORT`, never `localhost` (IPv6, silent failure).
- **nginx limits:** about 1 MB request bodies, so upload files in about 700 KB pieces and reassemble them. About 60-second timeouts, so use background jobs and polling.
- **PostgreSQL:**
  - Run `psql < file`, not `-f /root/file` (the postgres user can't read root's files).
  - After creating any table, re-grant to the app role.
  - Use `ADD COLUMN IF NOT EXISTS`.
- **Windows PowerShell 5.1 as the agent's local shell:** it mangles `$`, nested quotes and heredocs passed to `ssh`. Write a script file, `scp` it, and run it with `bash`. The owner's PC had no Python, so syntax-check on the server.
- **Claude API:**
  - Some Opus versions return HTTP 400 on a forced `tool_choice` (tool or any). Use `auto` and ask again in words.
  - If the app's own Python lacks the SDK, run each model call as a small subprocess under a separate virtualenv (JSON in, JSON out, key passed in the environment).
- **Chart.js:** an axis id starting with `r` is treated as a radial axis, so the lines silently don't draw. Use ids like `yRate`. Pin library versions.
- **CSS:** watch for class-name collisions between layout and table cells (a `.fc` layout class turned table headers into flex boxes). Add `[hidden]{display:none!important}`, because component `display` rules override the `hidden` attribute.
- **Wide tables:** put them in a scroll box the height of the window, with the first columns and the headers made sticky. Otherwise the sideways scroll bar sits at the bottom of a long page.
- **Phone photos:** turn them upright and shrink them in the browser (`createImageBitmap(file, {imageOrientation:'from-image'})` → canvas → JPEG) before uploading, so the server needs no image library.
- **Word files can be built with the standard library** (a zip of XML parts), including pictures. Verify by opening the result in real Word.
- **Preview pages without signing in:** stage the changed files into a copy of the app on the server, run it on a private port, fetch the pages and data with a server-made session, copy them down, and browse them locally. Never type the owner's passwords anywhere.

---

## 5. A starter checklist for a new client
1. Signed agreement covering data access and confidentiality. Get the client's own cloud account or server, so they own it.
2. Discovery: systems, the existing reports (the answer key), users, the data problems.
3. Server, database, firewall, TLS, backups, git and a `.env` on day one.
4. Sync scripts with a prune safety limit, a history capture, the analytical view and read-only logins.
5. The business-rules reference, plus `CLAUDE.md`.
6. Reproduce two or three of their existing reports to the cent, and show them side by side.
7. The first tool, with the client's lead user giving feedback weekly.
8. AI: an "Ask" chat on top of the data first (fast to show value), then proactive insights, then document drafting. Each gets its own key and cap.
9. A health page plus alerts for sync and backup failures. The reference case added these late; add them early.
10. Hand over: a written summary, the reference documents, a backup and restore test, and a costs sheet.

**Next sources the reference case planned but never reached:** accounting (Sage), HR (ADP) and project management (Procore). Each gets its own sync script and tables, then cross-system joins: CRM deal ↔ project ↔ invoice. Each source also needs a permission layer (role → allowed tables) before the data goes company-wide.

---

## 6. Open gaps from the reference case (lessons, not to-dos)
- One shared site password means no per-user identity. Plan SSO (Microsoft Entra or Google) from the start.
- Backups stayed on the same server, and no restore was ever tested.
- No alerting on failed syncs until late.
- Old secrets sat in git history. Never commit them in the first place.
- Data problems in the CRM can only be fixed by the client. A "clean-up list" tool (stale close dates, missing fields, duplicates, each linked to the record) is a strong early deliverable, because it makes every other tool more accurate.
