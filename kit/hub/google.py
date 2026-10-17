"""Sign in with Google (Google Workspace or any Google account), using OpenID Connect.

Turned on per install in config.toml:

    [auth]
    google_client_id = "....apps.googleusercontent.com"
    google_allowed_domain = "yourcompany.com"   # optional: only accounts on this Workspace domain
    public_url = "https://hub.yourcompany.com"  # the address people use (for Google's redirect)
    password_login = false                      # optional: turn passwords off once Google works

and GOOGLE_CLIENT_SECRET in the install's env file. Only people who already have a hub account (same email)
can sign in; signing in with Google never creates accounts by itself.

The ID token comes straight from Google's token endpoint over TLS in exchange for our client secret, so its
contents are trusted without checking the signature (OpenID Connect Core 3.1.3.7); we still check the issuer,
audience, expiry, nonce, verified email and domain.
"""
import base64
import hashlib
import json
import os
import secrets
import time
import urllib.parse
import urllib.request

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from ..config import _load_env_file, env_file, get_settings

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
STATE_COOKIE = "hub_google"
ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


class GoogleError(RuntimeError):
    """A sign-in problem; the message is safe to show."""


def config() -> dict:
    return get_settings().client.get("auth", {})


def enabled() -> bool:
    _load_env_file(env_file())
    return bool(config().get("google_client_id") and os.environ.get("GOOGLE_CLIENT_SECRET"))


def password_login_allowed() -> bool:
    return bool(config().get("password_login", True)) or not enabled()


def _signer():
    return URLSafeTimedSerializer(get_settings().session_secret, salt="google-login")


def redirect_uri(base_url: str) -> str:
    base = (config().get("public_url") or base_url).rstrip("/")
    return base + "/auth/google/callback"


def start(base_url: str, nxt: str) -> tuple[str, str]:
    """Return (Google URL to send the browser to, signed cookie value holding state, nonce and PKCE verifier)."""
    state, nonce, verifier = (secrets.token_urlsafe(24) for _ in range(3))
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    params = {"client_id": config()["google_client_id"], "redirect_uri": redirect_uri(base_url), "response_type": "code",
              "scope": "openid email profile", "state": state, "nonce": nonce, "code_challenge": challenge,
              "code_challenge_method": "S256", "prompt": "select_account"}
    if config().get("google_allowed_domain"):
        params["hd"] = config()["google_allowed_domain"]
    cookie = _signer().dumps({"state": state, "nonce": nonce, "verifier": verifier, "next": nxt})
    return AUTH_URL + "?" + urllib.parse.urlencode(params), cookie


def exchange_code(code: str, verifier: str, redirect: str) -> dict:
    """Swap the one-time code for tokens at Google. Separate so tests can replace it."""
    body = urllib.parse.urlencode({"code": code, "client_id": config()["google_client_id"],
                                   "client_secret": os.environ["GOOGLE_CLIENT_SECRET"], "redirect_uri": redirect,
                                   "grant_type": "authorization_code", "code_verifier": verifier}).encode()
    req = urllib.request.Request(TOKEN_URL, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception:
        raise GoogleError("Couldn't finish signing in with Google. Please try again.")


def _claims(id_token: str) -> dict:
    try:
        payload = id_token.split(".")[1]
        return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except Exception:
        raise GoogleError("Google sent back something we couldn't read. Please try again.")


def finish(base_url: str, cookie: str | None, state: str | None, code: str | None, exchange=exchange_code) -> tuple[str, str]:
    """Check everything and return (verified email, where to go next)."""
    if not cookie or not state or not code:
        raise GoogleError("That sign-in link expired. Please start again.")
    try:
        saved = _signer().loads(cookie, max_age=600)
    except (BadSignature, SignatureExpired):
        raise GoogleError("That sign-in link expired. Please start again.")
    if not secrets.compare_digest(saved["state"], state):
        raise GoogleError("That sign-in didn't match. Please start again.")
    tokens = exchange(code, saved["verifier"], redirect_uri(base_url))
    c = _claims(tokens.get("id_token", ""))
    if c.get("iss") not in ISSUERS or c.get("aud") != config()["google_client_id"]:
        raise GoogleError("That sign-in wasn't meant for this hub.")
    if int(c.get("exp", 0)) < time.time() or c.get("nonce") != saved["nonce"]:
        raise GoogleError("That sign-in expired. Please start again.")
    if not c.get("email_verified"):
        raise GoogleError("Your Google account's email isn't verified.")
    domain = config().get("google_allowed_domain")
    if domain and c.get("hd") != domain:
        raise GoogleError(f"Please sign in with your {domain} account.")
    return c["email"].lower(), saved.get("next") or "/"
