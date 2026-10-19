"""The public website.

    HUB_ENV_FILE=/etc/hub/website.env uvicorn website.app:app --host 127.0.0.1 --port 8000

Settings (in the env file): DATABASE_URL (the website's own login, which can only add enquiries),
SITE_SECRET, and optionally ALERT_NTFY_URL / ALERT_EMAIL_TO + SMTP_* (new-enquiry alerts) and HUB_URL
(the company hub's address, for the link in the alert).
"""
import hashlib
import logging
import os
import re
import threading
import time
from collections import defaultdict, deque
from pathlib import Path

import psycopg2
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from starlette.concurrency import run_in_threadpool

from kit.config import _load_env_file, env_file

from . import pages

log = logging.getLogger("website")
_load_env_file(env_file())
for key in ("DATABASE_URL", "SITE_SECRET"):
    if not os.environ.get(key):
        raise RuntimeError(f"Missing {key}; see website/app.py")
SECRET = os.environ["SITE_SECRET"]
EMAIL = re.compile(r"^[^@\s]{1,100}@[^@\s]{1,100}\.[a-zA-Z]{2,}$")
MIN_SECONDS, MAX_SECONDS = 3, 2 * 3600       # how long the form may have been open before sending
PER_IP_PER_HOUR = 5

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

def _demo_origins() -> str:
    """The demo hubs this site shows inside its pages (from [[demos]] in config.toml)."""
    from urllib.parse import urlsplit
    origins = {f"https://{urlsplit(d['url']).hostname}" for d in pages.cfg().get("demos", []) if d.get("url", "").startswith("https://")}
    return " ".join(sorted(origins)) or "'none'"


HEADERS = {
    "Content-Security-Policy": "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'none'; "
                               f"frame-src {_demo_origins()}; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
    "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Strict-Transport-Security": "max-age=31536000",
}
_recent: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()


@app.middleware("http")
async def headers(request: Request, call_next):
    response = await call_next(request)
    for k, v in HEADERS.items():
        response.headers.setdefault(k, v)
    if request.url.path.startswith("/static/"):
        response.headers.setdefault("Cache-Control", "public, max-age=86400")
    return response


def _signer():
    return URLSafeTimedSerializer(SECRET, salt="contact-form")


def form_token() -> str:
    return _signer().dumps({"t": time.time()})


def _ip_hash(request) -> str:
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "")
    return hashlib.sha256((SECRET + ip).encode()).hexdigest()[:32]


def _too_many(ip_hash: str) -> bool:
    now = time.monotonic()
    with _lock:
        q = _recent[ip_hash]
        while q and now - q[0] > 3600:
            q.popleft()
        if len(q) >= PER_IP_PER_HOUR:
            return True
        q.append(now)
    try:  # also check the database, so restarts and multiple workers can't be used to get around it
        with psycopg2.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM practice.inbound_leads WHERE ip_hash = %s AND created_at > now() - interval '1 hour'",
                        (ip_hash,))
            return cur.fetchone()[0] >= PER_IP_PER_HOUR
    except psycopg2.Error:
        return False


def save_lead(data: dict) -> None:
    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
        cur.execute("""INSERT INTO practice.inbound_leads (name, email, company, role, company_size, crm, interest, message,
                                                           source_page, ip_hash)
                       VALUES (%(name)s, %(email)s, %(company)s, %(role)s, %(company_size)s, %(crm)s, %(interest)s,
                               %(message)s, %(source_page)s, %(ip_hash)s)""", data)


def notify(data: dict) -> None:
    try:
        from kit.alerts import send
        hub = os.environ.get("HUB_URL", "").rstrip("/")
        msg = (f"{data['name']} ({data['email']})" + (f", {data['role']}" if data.get("role") else "")
               + (f" at {data['company']}" if data.get("company") else "") + f" wants: {data['interest_label']}."
               + (f" {hub}/inbox" if hub else ""))
        send("New website enquiry", msg, critical=True)
    except Exception:  # an alert problem must never lose the enquiry or show an error to the visitor
        log.exception("could not send enquiry alert")


def validate(form) -> tuple[dict, dict]:
    g = lambda k, n: (str(form.get(k) or "").strip())[:n]
    data = {"name": g("name", 120), "email": g("email", 200).lower(), "company": g("company", 160), "role": g("role", 120),
            "company_size": g("company_size", 40), "crm": g("systems", 200), "interest": g("interest", 40),
            "message": g("message", 3000)}
    data["systems"] = data["crm"]  # stored in the crm column; the form calls it "systems"
    errors = {}
    if len(data["name"]) < 2:
        errors["name"] = "Please add your name."
    if not EMAIL.match(data["email"]):
        errors["email"] = "Please add a valid email address."
    if data["company_size"] not in pages.SIZES:
        data["company_size"] = ""
    interests = dict(pages.INTERESTS)
    if data["interest"] not in interests:
        data["interest"] = "other"
    data["interest_label"] = interests[data["interest"]]
    if len(re.findall(r"https?://", data["message"])) > 2:
        errors["message"] = "Please keep links to two or fewer."
    return data, errors


@app.get("/", response_class=HTMLResponse)
def home():
    return pages.home()


@app.get("/demo", response_class=HTMLResponse)
def demos():
    return pages.demos()


@app.get("/demo/{slug}", response_class=HTMLResponse)
def demo_view(slug: str):
    page = pages.demo_view(slug)
    return HTMLResponse(page) if page else HTMLResponse(pages.not_found(), status_code=404)


@app.get("/what-we-build", response_class=HTMLResponse)
def what_we_build():
    return pages.what_we_build()


@app.get("/about", response_class=HTMLResponse)
def about():
    return pages.about()


@app.get("/privacy", response_class=HTMLResponse)
def privacy():
    return pages.privacy()


@app.get("/contact", response_class=HTMLResponse)
def contact(interest: str = ""):
    return pages.contact(form_token(), {"interest": interest})


@app.post("/contact", response_class=HTMLResponse)
async def contact_send(request: Request):
    form = await request.form()
    if form.get("website"):  # the honeypot: people never see this field, bots fill it in
        return RedirectResponse("/thanks", status_code=303)
    try:
        started = _signer().loads(str(form.get("token") or ""), max_age=MAX_SECONDS)["t"]
    except (BadSignature, SignatureExpired, KeyError, TypeError):
        return HTMLResponse(pages.contact(form_token(), dict(form), {"_form": "This form expired. Please press Send again."}),
                            status_code=400)
    if time.time() - started < MIN_SECONDS:
        return RedirectResponse("/thanks", status_code=303)  # faster than a person can type: treat as a bot
    data, errors = validate(form)
    if errors:
        return HTMLResponse(pages.contact(form_token(), data, errors), status_code=400)
    data["ip_hash"] = _ip_hash(request)
    data["source_page"] = (request.headers.get("referer") or "")[:300]
    if await run_in_threadpool(_too_many, data["ip_hash"]):
        return HTMLResponse(pages.contact(form_token(), data, {"_form": f"Too many messages from here. Please email {pages.cfg()['email']} instead."}),
                            status_code=429)
    try:
        await run_in_threadpool(save_lead, data)
    except psycopg2.Error:
        log.exception("could not save inquiry")
        return HTMLResponse(pages.contact(form_token(), data, {"_form": f"Something went wrong saving that. Please email {pages.cfg()['email']} instead."}),
                            status_code=500)
    threading.Thread(target=notify, args=(data,), daemon=True).start()
    return RedirectResponse(f"/thanks?n={data['name'].split()[0][:40]}", status_code=303)


@app.get("/thanks", response_class=HTMLResponse)
def thanks(n: str = ""):
    return pages.thanks(n)


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    return "User-agent: *\nDisallow: /demo\nAllow: /\n"   # demos are shared on request


@app.get("/healthz", response_class=PlainTextResponse)
def healthz():
    return "ok"


@app.exception_handler(404)
async def not_found(request, exc):
    return HTMLResponse(pages.not_found(), status_code=404)
