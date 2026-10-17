"""Sign-in, sessions and the security baseline for the hub.

- Each login gets its own server-side session (core.sessions); the cookie
  only carries a signed session id. Signing out or changing a password ends it.
- Cookies are HttpOnly, SameSite=Lax, and Secure unless SECURE_COOKIES=0.
- Wrong passwords are rate-limited per IP address.
- "Return to" addresses after sign-in must stay inside the site.

Microsoft or Google single sign-on slots in here later; the rest of the hub
only cares about request.state.user.
"""
import secrets
import threading
import time
from collections import defaultdict, deque

from itsdangerous import BadSignature, URLSafeSerializer

from .. import db
from ..config import get_settings
from ..passwords import check_password

COOKIE = "hub_session"
SESSION_HOURS = 12
MAX_FAILS = 8
FAIL_WINDOW = 15 * 60

_fails: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()


def _signer():
    return URLSafeSerializer(get_settings().session_secret, salt="hub-session")


def safe_next(target: str | None) -> str:
    """Only allow a path on this site: '/x' yes; '//evil', '/\\evil', 'http://...' no."""
    if not target or not target.startswith("/") or target.startswith("//") or target.startswith("/\\"):
        return "/"
    if any(c in target for c in "\r\n\\"):
        return "/"
    return target


def too_many_failures(ip: str) -> bool:
    now = time.monotonic()
    with _lock:
        q = _fails[ip]
        while q and now - q[0] > FAIL_WINDOW:
            q.popleft()
        return len(q) >= MAX_FAILS


def record_failure(ip: str):
    with _lock:
        _fails[ip].append(time.monotonic())


def clear_failures(ip: str):
    with _lock:
        _fails.pop(ip, None)


def authenticate(email: str, password: str) -> dict | None:
    user = db.one("SELECT id, password_hash, active FROM core.app_users WHERE email = lower(%(e)s)", {"e": email})
    ok = check_password(password, user["password_hash"] if user else None)
    if not user or not ok or not user["active"]:
        return None
    return user


def start_session(user_id: int) -> str:
    sid = secrets.token_urlsafe(32)
    with db.connect() as conn:
        db.execute("""INSERT INTO core.sessions (id, user_id, expires_at)
                      VALUES (%(s)s, %(u)s, now() + make_interval(hours => %(h)s))""",
                   {"s": sid, "u": user_id, "h": SESSION_HOURS}, conn)
        db.execute("UPDATE core.app_users SET last_login_at = now() WHERE id = %(u)s", {"u": user_id}, conn)
        db.execute("DELETE FROM core.sessions WHERE expires_at < now()", None, conn)
    return _signer().dumps(sid)


def end_session(cookie: str | None):
    sid = _unsign(cookie)
    if sid:
        db.execute("DELETE FROM core.sessions WHERE id = %(s)s", {"s": sid})


def _unsign(cookie: str | None) -> str | None:
    if not cookie:
        return None
    try:
        return _signer().loads(cookie)
    except BadSignature:
        return None


def user_from_cookie(cookie: str | None) -> dict | None:
    sid = _unsign(cookie)
    if not sid:
        return None
    return db.one("""SELECT u.id, u.email, u.name, u.role, u.branches FROM core.sessions s
                     JOIN core.app_users u ON u.id = s.user_id
                     WHERE s.id = %(s)s AND s.expires_at > now() AND u.active""", {"s": sid})


def cookie_kwargs() -> dict:
    return {"httponly": True, "samesite": "lax", "secure": get_settings().secure_cookies,
            "max_age": SESSION_HOURS * 3600, "path": "/"}


SECURITY_HEADERS = {
    "Content-Security-Policy": ("default-src 'self'; script-src 'self' 'unsafe-inline'; "
                                "style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; "
                                "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}
