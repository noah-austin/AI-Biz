# Website

The public site: `website/app.py` serves the pages in `website/pages.py` (with styles in `website/static/site.css`), and its
contact form saves enquiries into the company hub's `practice.inbound_leads` table. They appear in the hub's Inbox
and trigger a phone alert.

- Edit the words in `website/pages.py` and the name and email in `website/config.toml`.
- The site's database login can only add enquiries; it can't read or change anything else.
- Spam protection: a hidden honeypot field, a minimum time on the page, a signed form token, and a limit of 5
  enquiries per visitor per hour.
- On the server: `sudo ops/install.sh website <domain> [hub-name]` (see `ops/install.sh`).
- Run it locally: `HUB_ENV_FILE=<site env file> uvicorn website.app:app --port 8000`.
