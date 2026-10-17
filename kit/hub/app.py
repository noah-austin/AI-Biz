"""The hub web app.

    uvicorn kit.hub.app:app --host 127.0.0.1 --port 8000

It listens on localhost only; nginx with HTTPS sits in front on a real server.
"""
import logging
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from .. import db
from ..ai import chat, usage as ai_usage
from ..config import get_settings
from . import auth, pages, ui

log = logging.getLogger("hub")
settings = get_settings()  # fail loudly at start-up if anything is missing
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

PUBLIC = ("/login", "/static/", "/healthz")


@app.middleware("http")
async def gatekeeper(request: Request, call_next):
    path = request.url.path
    request.state.user = None
    if not path.startswith(PUBLIC):
        user = await run_in_threadpool(auth.user_from_cookie, request.cookies.get(auth.COOKIE))
        if not user:
            if request.method == "GET":
                nxt = path + (f"?{request.url.query}" if request.url.query else "")
                from urllib.parse import quote
                return RedirectResponse(f"/login?next={quote(nxt, safe='')}", status_code=303)
            return PlainTextResponse("Sign in first.", status_code=401)
        request.state.user = user
    response = await call_next(request)
    for k, v in auth.SECURITY_HEADERS.items():
        response.headers.setdefault(k, v)
    if settings.secure_cookies:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
    if request.state.user and request.method == "GET" and response.status_code == 200 \
            and not path.startswith(("/static/", "/demo-source/", "/ai/")) and not path.endswith(".csv"):
        try:
            await run_in_threadpool(db.execute, "INSERT INTO core.page_visits (user_id, path) VALUES (%(u)s, %(p)s)",
                                    {"u": request.state.user["id"], "p": path})
        except Exception:  # usage tracking must never break a page
            log.exception("could not record visit")
    return response


def _login_page(error="", nxt="/"):
    client = settings.client
    err = f'<p class="error" role="alert">{ui.esc(error)}</p>' if error else ""
    demo = ('<p class="muted" style="font-size:13px">This is a demo with a fictional company and made-up data.</p>'
            if settings.is_demo else "")
    return ui.bare_page("Sign in", f"""<div class="signin">
<div class="brand" style="margin-bottom:14px"><span class="mark" aria-hidden="true"></span></div>
<h1 style="margin-bottom:4px">{ui.esc(client.get("short_name", "Hub"))} Hub</h1>
<p class="muted" style="margin-top:0">{ui.esc(client.get("company", ""))}</p>{demo}{err}
<form method="post" action="/login"><input type="hidden" name="next" value="{ui.esc(auth.safe_next(nxt))}">
<label>Email<input type="email" name="email" autocomplete="username" required autofocus></label>
<label>Password<input type="password" name="password" autocomplete="current-password" required></label>
<button class="primary" type="submit">Sign in</button></form></div>""")


@app.get("/login", response_class=HTMLResponse)
def login_form(next: str = "/"):
    return _login_page(nxt=next)


@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), next: str = Form("/")):
    ip = request.client.host if request.client else "unknown"
    if auth.too_many_failures(ip):
        return HTMLResponse(_login_page("Too many attempts. Wait 15 minutes and try again.", next), status_code=429)
    user = auth.authenticate(email, password)
    if not user:
        auth.record_failure(ip)
        return HTMLResponse(_login_page("That email and password don't match.", next), status_code=401)
    auth.clear_failures(ip)
    resp = RedirectResponse(auth.safe_next(next), status_code=303)
    resp.set_cookie(auth.COOKIE, auth.start_session(user["id"]), **auth.cookie_kwargs())
    return resp


@app.post("/logout")
def logout(request: Request):
    auth.end_session(request.cookies.get(auth.COOKIE))
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie(auth.COOKIE, path="/")
    return resp


@app.get("/healthz", response_class=PlainTextResponse)
def healthz():
    """For an uptime monitor: is the app up and is the data fresh? Reveals nothing else."""
    r = db.one("""SELECT count(*) FILTER (WHERE last_status = 'failed' OR last_success_at < now() - interval '3 hours') AS bad
                  FROM core.sync_state WHERE object <> 'backup'""")
    synced = db.one("SELECT count(*) AS n FROM core.sync_state WHERE object <> 'backup'")["n"]
    ok = bool(synced) and not r["bad"]
    return PlainTextResponse("ok" if ok else "stale", status_code=200 if ok else 503)


def _html(fn):
    def handler(request: Request):
        return HTMLResponse(fn(request))
    return handler


app.get("/", response_class=HTMLResponse)(_html(pages.home))
app.get("/scorecard", response_class=HTMLResponse)(_html(pages.scorecard))
app.get("/deals", response_class=HTMLResponse)(_html(pages.deals))
app.get("/winloss", response_class=HTMLResponse)(_html(pages.winloss))
app.get("/receivables", response_class=HTMLResponse)(_html(pages.receivables))
app.get("/invoices", response_class=HTMLResponse)(_html(pages.invoices))
app.get("/cleanup", response_class=HTMLResponse)(_html(pages.cleanup_page))


@app.get("/deals.csv")
def deals_csv(request: Request):
    return Response(pages.deals_csv(request), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="deals.csv"'})


@app.get("/health", response_class=HTMLResponse)
def health(request: Request):
    if request.state.user["role"] != "admin":
        return HTMLResponse(ui.page(request, "Not allowed", '<section class="card">Only admins can see this page.</section>'),
                            status_code=403)
    return HTMLResponse(pages.health(request))


# ---------------------------------------------------------------- AI "Ask" chat

def _ai_guard(request: Request):
    # A custom header can't be sent cross-site without the browser asking first, which blocks CSRF.
    if request.headers.get("x-hub") != "1":
        return JSONResponse({"error": "Bad request."}, status_code=400)
    return None


@app.get("/ai/status")
def ai_status(request: Request):
    user = request.state.user
    return {"enabled": ai_usage.is_configured("chat"), "admin": user["role"] == "admin",
            "suggestions": chat.suggestions(user)}


@app.post("/ai/ask")
async def ai_ask(request: Request):
    if (bad := _ai_guard(request)) is not None:
        return bad
    try:
        body = await request.json()
    except ValueError:
        return JSONResponse({"error": "Bad request."}, status_code=400)
    try:
        ids = await run_in_threadpool(chat.start, request.state.user, str(body.get("question") or ""),
                                      body.get("conversation_id") or None, str(body.get("page") or ""))
    except (ValueError, ai_usage.CapReached) as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    return ids


@app.get("/ai/jobs/{job_id}")
def ai_job(request: Request, job_id: str):
    j = chat.job_status(job_id, request.state.user)
    return j if j else JSONResponse({"error": "Not found."}, status_code=404)


@app.get("/ai/conversations/{conversation_id}")
def ai_conversation(request: Request, conversation_id: str):
    return {"turns": chat.history(conversation_id, request.state.user)}


if settings.is_demo:
    @app.get("/demo-source/{system}/{obj}/{rec_id}", response_class=HTMLResponse)
    def demo_source(request: Request, system: str, obj: str, rec_id: str):
        return HTMLResponse(pages.demo_source(request, system, obj, rec_id))
