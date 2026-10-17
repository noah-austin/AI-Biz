# Our own server: setup

One server for the business: the company hub (to run the business on), the Bluestem demo, and later the website. **Demo data and our own data only; client data never goes here.**

Claude Code runs *on* the server, linked to Noah's Claude account with Remote Control, so it shows up in the Claude app (desktop and phone). Usage counts toward the Claude subscription, not the API.

## Part 1: Noah (about 20 minutes, copy-paste)

**1. Create the server** on DigitalOcean (its in-browser console supports copy-paste):
- Create → Droplets → **Ubuntu 24.04 LTS**, in the US region closest to you.
- Size: Basic, Regular, **4 GB RAM / 2 CPUs** (about $24 a month). Claude Code needs 4 GB.
- Authentication: Password. Make it strong and save it in a password manager.
- Tick **Backups** (weekly, about $5 a month more).
- Hostname: `biz-server`.

**2. Open the console:** click the droplet, then Access → **Launch Droplet Console**.

**3. Paste this block** (it runs as the administrator):
```bash
apt update && apt -y upgrade && apt -y install tmux git gh ufw unattended-upgrades
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw --force enable
adduser --disabled-password --gecos "" noah && usermod -aG sudo noah
echo "noah ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/noah && chmod 440 /etc/sudoers.d/noah
su - noah
```

**4. Install Claude Code** (now as `noah`):
```bash
curl -fsSL https://claude.ai/install.sh | bash
exec bash
claude --version
```

**5. Connect GitHub** so the server can get our code:
```bash
gh auth login
```
Choose **GitHub.com → HTTPS → Login with a web browser**. It shows a code; open github.com/login/device on your phone and enter it. Then:
```bash
gh repo clone noah-austin/AI-Biz ~/AI-Biz && cd ~/AI-Biz
```

**6. Sign in to Claude:** run `claude`, type `/login`, and choose your Claude account (Pro/Max). Press `c` to copy the link, open it on your phone, sign in, and paste back the code it shows. Type `/exit` when done.

**7. Start Remote Control**, inside tmux so it keeps running after you close the console:
```bash
tmux new -s claude
claude remote-control --name "Biz server"
```
Answer `y` to enable it. Then press **Ctrl+b**, then **d**, to leave it running in the background. You can close the console.

**8. Open the Claude app** → Code → **Biz server** (computer icon with a green dot). Send:
> Set up this server by following docs/server-setup.md, Part 2.

**If the server restarts:** open the console and run `su - noah`, `tmux new -s claude`, `cd ~/AI-Biz`, then `claude remote-control --continue`.

**Keep your Claude and GitHub accounts protected with two-factor sign-in.** Whoever controls them controls this server.

## Part 2: for the Claude session on the server

Work in plain English with Noah. Ask before anything hard to undo. Follow `CLAUDE.md`.

1. **Check the basics:** Ubuntu updates on; `unattended-upgrades` enabled for security patches; firewall allows only 22, 80 and 443. Disable SSH password login once Noah has an SSH key; until then the provider console is the way in.
2. **Install:** PostgreSQL 16 (listening on localhost only), Python 3 with a virtualenv at `~/AI-Biz/venv` (`pip install -r requirements.txt`), Caddy as the web front end (automatic HTTPS).
3. **Databases:** one per install (`hub_company`, `hub_demo`), each with its own app role and its own `ai_reader` role. Secrets go in a root-only `.env` per install, never in git.
4. **Installs:** run each kit install as its own systemd service on its own localhost port:
   - **company hub** (`clients/company/`, once that folder exists) on 8001;
   - **Bluestem demo** (`clients/demo/`) on 8002.
5. **Web addresses:** until there's a domain, use `<ip-with-dashes>.sslip.io` hostnames (for example `company.1-2-3-4.sslip.io`) so Caddy can get real HTTPS certificates. Switch to the business domain when it exists.
6. **Scheduled jobs (cron):**
   - hourly sync for each install;
   - for the demo, `clients/demo/generate.py` daily before its sync, so the fake company moves forward;
   - nightly `ops/backup.sh` for each database;
   - the weekly restore test;
   - AI insights once API keys exist.
7. **Off-site backups:** a DigitalOcean Spaces bucket via `OFFSITE_CMD` (ask Noah to create it), on top of the droplet's weekly snapshots.
8. **Health:** confirm `/healthz` for each install, and set up a free uptime monitor that emails Noah if it fails.
9. **Users:** create Noah's admin login on each install with `python -m kit.manage create-user`; he types the password himself.
10. **Finish:** write `docs/server-notes.md` (what's installed, ports, service names, how to deploy and roll back; no secrets), commit and push it, and give Noah the links.

**Deploy routine afterwards:** `git pull` → run tests → `python -m kit.manage init-db` for each install → restart its service → check `/healthz` and the logs → roll back with `git revert` if anything is wrong.
