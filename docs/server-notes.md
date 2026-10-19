# Our server: notes

How our own server is set up (from `docs/server-setup.md`, Part 2). No secrets here: they live in `/etc/hub/*.env` on the server only.

## The machine
- DigitalOcean droplet, Ubuntu 24.04, 4 GB / 2 CPUs, weekly DigitalOcean backups.
- User `noah` (passwordless sudo). Code in `/home/noah/AI-Biz`, Python in `venv/`.
- Firewall: only SSH (22), 80 and 443 open. Automatic security updates on.
- Claude Code runs as `noah` with Remote Control, named **Biz server**. It starts at boot and restarts if it exits: user service `claude-remote` (`~/.config/systemd/user/claude-remote.service`, lingering on). Reboot-tested 2026-10-19. Logs: `journalctl --user -u claude-remote`.

## What's installed

| Install | Address | Local port | Service | Database |
|---|---|---|---|---|
| Company hub | https://hub.sanfordoperations.com | 8001 | `hub-company` | `hub_company` |
| Bluestem demo | https://demo.sanfordoperations.com | 8002 | `hub-demo` | `hub_demo` |
| Distribution demo (Bramblewood) | https://distribution.demo.sanfordoperations.com | 8003 | `hub-distribution` | `hub_distribution` |
| Website | https://sanfordoperations.com (www redirects) | 8000 | `hub-website` | writes enquiries into `hub_company` |

Demos: the website's "See a live demo" goes to https://sanfordoperations.com/demo, a picker listing each industry's demo
(`[[demos]]` in `website/config.toml`). Each demo is its own install from `clients/demo_<industry>/`, at
`<industry>.demo.sanfordoperations.com` (a wildcard DNS record `*.demo` points every such address here; Caddy gets each
certificate on first use). Bluestem stays at demo.sanfordoperations.com. To add one: build it in `~/AI-Biz-dev`, bring it
across, then `sudo ops/install.sh add <name> clients/demo_<name> <next port> <name>.demo.sanfordoperations.com`, set its
`ALERT_NTFY_URL`, and add its card to `website/config.toml`. Development databases for demos (`hub_dev_*`, env files
`~/AI-Biz-dev/*.env`) are for building only.

- PostgreSQL listens on localhost only. Caddy serves HTTPS and renews certificates itself (`/etc/caddy/sites/*.caddy`).
- Settings per install: `/etc/hub/NAME.env` (owner-only). The website's database login can only add enquiries.
- Scheduled jobs: `/etc/cron.d/hub-company`, `/etc/cron.d/hub-demo` (alerts every 15 min, nightly backup 07:30 UTC, weekly restore test Sunday 09:00 UTC; the demo also regenerates and syncs its data, the hub runs agents).
- Logs: `/var/log/hub/` (rotated weekly). Service logs: `journalctl -u hub-NAME`.
- Backups: `/var/backups/hub/NAME/`, kept 14 days.
- Alerts: a private ntfy topic (in each env file as `ALERT_NTFY_URL`) on Noah's phone, for problems and new website enquiries. Tested 2026-10-19.

## The assistant
- Claude Code on this server (Noah's subscription) is the business assistant. It works on the company hub through
  `bin/hub` (see `.claude/skills/hub/SKILL.md`): reads anything, proposes into the Inbox, and makes changes only after
  Noah confirms. The ideal client is stored in the hub (`practice.settings`) and changed by chat.
- Scheduled agent jobs still use the API runner (`kit.agents tick`) and do nothing until `ANTHROPIC_API_KEY_AGENTS` is set.
- Tests: `.env` in the repo points at a separate `hub_test` database (demo data). Tests wipe tables there; never point
  `.env` at a real install.

## Everyday commands
- What's running: `ops/install.sh list`
- Health: `curl -s http://127.0.0.1:8001/healthz` (8002 for the demo)
- Restart one: `sudo systemctl restart hub-company`

## Deploy and roll back
The live sites run from `~/AI-Biz`, so build in the separate working copy `~/AI-Biz-dev` (git worktree on its own
branch, with its own `.env` pointing at the `hub_test` database) and only bring finished, tested work across:
`git merge --ff-only <branch>` in `~/AI-Biz`, push, then update. Editing `~/AI-Biz` directly changes what the
live demo's hourly sync reads straight away.
1. Push the change, run the tests, then on the server: `cd ~/AI-Biz && sudo ops/install.sh update`. It pulls, upgrades each database, restarts each service and prints its health.
2. If something's wrong: `git revert <bad commit>`, push, and run `update` again.

## Still to do
- API keys (`kit.manage set-secret`): `ANTHROPIC_API_KEY_CHAT` and `ANTHROPIC_API_KEY_AGENTS` on the hub, `ANTHROPIC_API_KEY_CHAT` on the demo.
- Off-site backups: a DigitalOcean Spaces bucket, then `OFFSITE_CMD` in each env file.
- External uptime monitor on each `/healthz`, emailing Noah.
- Google sign-in, once the OAuth client exists.

## If Remote Control doesn't come back after a restart
Open the DigitalOcean console, then: `su - noah`, `tmux new -s claude`, `cd ~/AI-Biz`, `claude remote-control --name "Biz server"`, then Ctrl+b, d.
