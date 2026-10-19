# Our server: notes

How our own server is set up (from `docs/server-setup.md`, Part 2). No secrets here: they live in `/etc/hub/*.env` on the server only.

## The machine
- DigitalOcean droplet, Ubuntu 24.04, 4 GB / 2 CPUs, weekly DigitalOcean backups.- User `noah` (passwordless sudo). Code in `/home/noah/AI-Biz`, Python in `venv/`.
- Firewall: only SSH (22), 80 and 443 open. Automatic security updates on.
- Claude Code runs as `noah` with Remote Control, named **Biz server**. It starts at boot and restarts if it exits: user service `claude-remote` (`~/.config/systemd/user/claude-remote.service`, lingering on). Reboot-tested 2026-10-19. Logs: `journalctl --user -u claude-remote`.

## What's installed

| Install | Address | Local port | Service | Database |
|---|---|---|---|---|
| Company hub | https://hub.sanfordoperations.com | 8001 | `hub-company` | `hub_company` |
| Bluestem demo | https://demo.sanfordoperations.com | 8002 | `hub-demo` | `hub_demo` |
| Website | https://sanfordoperations.com (www redirects) | 8000 | `hub-website` | writes enquiries into `hub_company` |

- PostgreSQL listens on localhost only. Caddy serves HTTPS and renews certificates itself (`/etc/caddy/sites/*.caddy`).
- Settings per install: `/etc/hub/NAME.env` (owner-only). The website's database login can only add enquiries.
- Scheduled jobs: `/etc/cron.d/hub-company`, `/etc/cron.d/hub-demo` (alerts every 15 min, nightly backup 07:30 UTC, weekly restore test Sunday 09:00 UTC; the demo also regenerates and syncs its data, the hub runs agents).
- Logs: `/var/log/hub/` (rotated weekly). Service logs: `journalctl -u hub-NAME`.
- Backups: `/var/backups/hub/NAME/`, kept 14 days.

## Everyday commands
- What's running: `ops/install.sh list`
- Health: `curl -s http://127.0.0.1:8001/healthz` (8002 for the demo)
- Restart one: `sudo systemctl restart hub-company`

## Deploy and roll back
1. Push the change, run the tests, then on the server: `cd ~/AI-Biz && sudo ops/install.sh update`. It pulls, upgrades each database, restarts each service and prints its health.
2. If something's wrong: `git revert <bad commit>`, push, and run `update` again.

## Still to do
- Admin logins for Noah on the hub and the demo (he types the password).
- API keys and the ntfy alert topic (`kit.manage set-secret`), then `kit.alerts test` and a test enquiry from the website's contact form.
- Off-site backups: a DigitalOcean Spaces bucket, then `OFFSITE_CMD` in each env file.
- External uptime monitor on each `/healthz`, emailing Noah.
- Google sign-in, once the OAuth client exists.

## If Remote Control doesn't come back after a restart
Open the DigitalOcean console, then: `su - noah`, `tmux new -s claude`, `cd ~/AI-Biz`, `claude remote-control --name "Biz server"`, then Ctrl+b, d.
