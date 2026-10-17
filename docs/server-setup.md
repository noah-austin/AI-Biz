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
gh repo clone noah-austin/AI-Biz ~/AI-Biz -- -b claude/new-business-brainstorm-vt7nkx && cd ~/AI-Biz
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

Work in plain English with Noah. Ask before anything hard to undo. Follow `CLAUDE.md`. `ops/install.sh` does the heavy lifting; read it first.

1. **Base setup:** `sudo ops/install.sh server`. It installs:
   - PostgreSQL (localhost only), Python in `venv/` and Caddy (automatic HTTPS);
   - the firewall (22, 80, 443) and automatic security updates;
   - log rotation.
2. **Installs:**
   - `sudo ops/install.sh add company clients/company 8001 auto`: Noah's company hub (practice tracker and agents).
   - `sudo ops/install.sh add demo clients/demo 8002 auto`: the Bluestem demo.

   Each gets its own database and logins, settings file (`/etc/hub/NAME.env`), service, scheduled jobs and an HTTPS address on `sslip.io`. Swap to the real domain once it exists: re-run `add` with the hostname.
   - Once the domain exists: `sudo ops/install.sh website yourcompany.com company`. It sets up the public website, saving enquiries into the company hub. Also re-run `add company … hub.yourcompany.com` and `add demo … demo.yourcompany.com` for the real addresses, and set `demo_url` in `website/config.toml` to `https://demo.yourcompany.com/guest`.
3. **Logins:** have Noah create his admin login on each install with the command the installer prints. He types the password himself.
4. **Keys and alerts**, typed hidden by Noah with `kit.manage set-secret` (the installer prints the exact form):
   - `ANTHROPIC_API_KEY_CHAT` and `ANTHROPIC_API_KEY_AGENTS` on the company hub, and `ANTHROPIC_API_KEY_CHAT` on the demo;
   - `ALERT_NTFY_URL` on both: a private ntfy topic Noah subscribes to in the ntfy phone app. Then run `kit.alerts test` to confirm a message arrives.
5. **Off-site backups:** ask Noah to create a DigitalOcean Spaces bucket, then set `OFFSITE_CMD` in each env file. Nightly backups and the weekly restore test are already scheduled.
6. **Keep Remote Control always on:** make `claude remote-control --name "Biz server"` (run in `~/AI-Biz` as `noah`) start at boot and restart if it exits: a systemd user service with lingering enabled, or tmux started by `@reboot` cron plus a watchdog. This isn't an official Anthropic feature, so test it with a real reboot before calling it done.
7. **Uptime:** set up a free external uptime monitor on each install's `/healthz` that emails Noah.
8. **Finish:** write `docs/server-notes.md` (what's installed, ports, addresses, how to deploy and roll back; no secrets), commit and push it, and give Noah the links.

**Google sign-in** (once Workspace exists):
- Create an OAuth client in Google Cloud (Web application) with the redirect URI `https://<host>/auth/google/callback`.
- Put `google_client_id`, `google_allowed_domain` and `public_url` under `[auth]` in the client's `config.toml`, and set `GOOGLE_CLIENT_SECRET` with `set-secret`.
- Restart the service. Once Google sign-in works, set `password_login = false`.

**Deploy routine afterwards:** run the tests, then `sudo ops/install.sh update`. It pulls the code, upgrades every install's database, restarts each service and checks `/healthz`. If anything is wrong, `git revert` the bad commit and run `update` again.
