import base64
import json
import time

import pytest

from kit import alerts, db
from kit.hub import google


def token(**claims):
    base = {"iss": "https://accounts.google.com", "aud": "cid.apps.googleusercontent.com", "exp": time.time() + 600,
            "email": "Noah@Example.com", "email_verified": True, "hd": "example.com"}
    base.update(claims)
    body = base64.urlsafe_b64encode(json.dumps(base).encode()).decode().rstrip("=")
    return f"x.{body}.sig"


@pytest.fixture
def google_on(monkeypatch):
    monkeypatch.setattr(google, "config", lambda: {"google_client_id": "cid.apps.googleusercontent.com",
                                                   "google_allowed_domain": "example.com"})
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "s")


def run_flow(nonce_ok=True, **claims):
    url, cookie = google.start("https://hub.example.com/", "/pipeline")
    from urllib.parse import parse_qs, urlparse
    q = {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}
    assert q["code_challenge_method"] == "S256" and q["hd"] == "example.com"
    assert q["redirect_uri"] == "https://hub.example.com/auth/google/callback"
    nonce = q["nonce"] if nonce_ok else "other"
    return google.finish("https://hub.example.com/", cookie, q["state"], "code",
                         exchange=lambda code, verifier, redirect: {"id_token": token(nonce=nonce, **claims)})


def test_google_sign_in_happy_path(google_on):
    assert run_flow() == ("noah@example.com", "/pipeline")


@pytest.mark.parametrize("bad", [
    {"aud": "someone-else"}, {"iss": "https://evil.example"}, {"exp": 1}, {"email_verified": False}, {"hd": "gmail.com"},
])
def test_google_sign_in_refuses_bad_tokens(google_on, bad):
    with pytest.raises(google.GoogleError):
        run_flow(**bad)


def test_google_refuses_wrong_nonce_and_state(google_on):
    with pytest.raises(google.GoogleError):
        run_flow(nonce_ok=False)
    url, cookie = google.start("https://hub.example.com/", "/")
    with pytest.raises(google.GoogleError):
        google.finish("https://hub.example.com/", cookie, "wrong-state", "code", exchange=lambda *a: {})
    with pytest.raises(google.GoogleError):
        google.finish("https://hub.example.com/", "tampered", "s", "code", exchange=lambda *a: {})


def test_alerts_send_once_then_resolve():
    db.execute("DELETE FROM core.alerts")
    db.execute("""INSERT INTO core.sync_state (object, source, last_status, last_message, last_attempt_at)
                  VALUES ('test.object', 'test', 'failed', 'boom', now())
                  ON CONFLICT (object) DO UPDATE SET last_status = 'failed', last_message = 'boom'""")
    sent = []
    deliver = lambda title, msg, critical=False: sent.append((title, msg)) or ["test"]
    r1 = alerts.check(deliver)
    assert "syncs" in r1["sent"] and any("boom" in m for _, m in sent)
    r2 = alerts.check(deliver)
    assert "syncs" not in r2["sent"]  # not repeated within 24 hours
    db.execute("DELETE FROM core.sync_state WHERE object = 'test.object'")
    sent.clear()
    r3 = alerts.check(deliver)
    assert "syncs" in r3["resolved"] and sent and sent[0][0] == "Hub: fixed"
    db.execute("DELETE FROM core.alerts")


def test_alerts_without_a_channel_wait_until_one_exists():
    db.execute("DELETE FROM core.alerts")
    db.execute("""INSERT INTO core.sync_state (object, source, last_status, last_message, last_attempt_at)
                  VALUES ('test.object2', 'test', 'failed', 'x', now()) ON CONFLICT (object) DO NOTHING""")
    alerts.check(lambda *a, **k: [])
    assert db.one("SELECT last_sent FROM core.alerts WHERE key = 'syncs'")["last_sent"] is None
    db.execute("DELETE FROM core.sync_state WHERE object = 'test.object2'")
    db.execute("DELETE FROM core.alerts")
