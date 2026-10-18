# Working rules for this repo

This is the home base for **Sanford Operations** (sanfordoperations.com), Noah's consulting business (data → tools → AI for small and mid-size companies).

- Noah is the owner. Talk in plain English, outcome first, and keep it short (he often reads on a phone).
- Ask before sizeable work, offering 2–4 options with a recommendation. Decide small things yourself and say what you decided.
- `docs/playbook-v0.md` is guidance, not law. Improve the method as we learn.
- Record business decisions in `docs/decisions.md`.
- **Confidentiality:** never put a client's name, data, figures, credentials or identifying details into this repo or into another client's work. The first reference client stays anonymous.
- No secrets in git, ever.

## The code
- `kit/` is the reusable system we install per client; `clients/<name>/` holds one client's settings and rulebook; `clients/demo/` is the fictional Bluestem demo. See `kit/README.md`.
- Stack: plain Python, FastAPI, PostgreSQL with raw SQL (psycopg2). No ORM, no front-end build step. Keep it that simple.
- Every number is defined once in `kit/metrics.py` (or the views in `kit/schema/050_views.sql`), and the client's rulebook says the same thing in words. Change both together.
- Before changing a number's definition, show the owner before/after figures and get a yes.
- Run `python -m pytest -q tests` before committing. Tests need a local PostgreSQL with the demo loaded (see `kit/README.md`).
- Visually check pages (desktop, phone and dark mode) after UI changes.
- Never commit `.env`, backups or generated source data (`clients/*/source/`).
- On client servers: take a backup before any UPDATE/DELETE/ALTER/DROP, show the statement and how many rows it touches, and wait for a yes.
