"""Website tests: pages, the contact form, spam protection, and the hub side of enquiries."""
import os
import time

import pytest

from kit import db


@pytest.fixture(scope="module")
def site():
    from kit.config import get_settings
    os.environ.setdefault("SITE_SECRET", "test-secret-for-the-website-only")
    os.environ["DATABASE_URL"] = get_settings().database_url
    from fastapi.testclient import TestClient
    from website import app as site_app
    yield TestClient(site_app.app), site_app
    db.execute("DELETE FROM practice.inbound_leads WHERE email LIKE '%%@site-test.example'")


def token(site_app, age=10):
    return site_app._signer().dumps({"t": time.time() - age})


def post(client, site_app, **fields):
    data = {"token": token(site_app), "name": "Robin Tester", "email": "robin@site-test.example", "interest": "call", **fields}
    return client.post("/contact", data=data, follow_redirects=False)


def count(email="robin@site-test.example"):
    return db.one("SELECT count(*) AS n FROM practice.inbound_leads WHERE email = %(e)s", {"e": email})["n"]


def test_pages_render_with_security_headers(site):
    client, _ = site
    for path in ["/", "/what-we-build", "/about", "/contact", "/privacy"]:
        r = client.get(path)
        assert r.status_code == 200, path
    assert "script-src 'none'" in r.headers["content-security-policy"]
    assert client.get("/nope").status_code == 404


def test_home_graphics_and_images_are_served(site):
    client, _ = site
    html = client.get("/").text
    assert 'class="hub-diagram"' in html and "style=" not in html  # the policy blocks inline styles
    assert html.count('class="faq"') == 7 and 'rel="canonical"' in html
    import re
    for src in set(re.findall(r'(?:src|srcset)="(/static/[^"]+)"', html)):
        assert client.get(src).status_code == 200, src


def test_real_enquiry_is_saved(site, monkeypatch):
    client, site_app = site
    monkeypatch.setattr(site_app, "notify", lambda data: None)
    before = count()
    r = post(client, site_app, company="Test Co", systems="HubSpot, QuickBooks", message="Hello")
    assert r.status_code == 303 and r.headers["location"].startswith("/thanks")
    assert count() == before + 1
    assert db.one("SELECT crm FROM practice.inbound_leads ORDER BY id DESC LIMIT 1")["crm"] == "HubSpot, QuickBooks"


def test_bots_are_dropped_quietly(site, monkeypatch):
    client, site_app = site
    monkeypatch.setattr(site_app, "notify", lambda data: None)
    before = count("bot@site-test.example")
    r1 = post(client, site_app, email="bot@site-test.example", website="spam.example")       # honeypot filled in
    fast = {"token": token(site_app, age=0), "name": "Fast Bot", "email": "bot@site-test.example"}
    r2 = client.post("/contact", data=fast, follow_redirects=False)                          # sent too quickly
    r3 = client.post("/contact", data={**fast, "token": "forged"}, follow_redirects=False)  # bad token
    assert r1.status_code == 303 and r2.status_code == 303 and r3.status_code == 400
    assert count("bot@site-test.example") == before


def test_validation_and_rate_limit(site, monkeypatch):
    client, site_app = site
    monkeypatch.setattr(site_app, "notify", lambda data: None)
    assert post(client, site_app, email="not-an-email").status_code == 400
    assert post(client, site_app, message="http://a http://b http://c").status_code == 400
    site_app._recent.clear()
    db.execute("DELETE FROM practice.inbound_leads WHERE email LIKE '%%@site-test.example'")
    codes = [post(client, site_app, email="limit@site-test.example").status_code for _ in range(7)]
    assert codes.count(303) == site_app.PER_IP_PER_HOUR and codes[-1] == 429


def test_hub_turns_an_enquiry_into_a_prospect():
    from kit.practice import inbox
    db.execute("""INSERT INTO practice.inbound_leads (name, email, company, role, interest, message)
                  VALUES ('Sam Lead', 'sam@site-test.example', 'Lead Test Co', 'CFO', 'call', 'Help')""")
    lid = db.one("SELECT id FROM practice.inbound_leads WHERE email = 'sam@site-test.example'")["id"]
    nxt = inbox.decide_lead(lid, "add")
    c = db.one("SELECT id, kind, stage, source, contact_email FROM practice.companies WHERE name = 'Lead Test Co'")
    assert nxt == f"/companies/{c['id']}" and (c["kind"], c["stage"], c["source"]) == ("prospect", "contacted", "Website")
    assert db.one("SELECT status FROM practice.inbound_leads WHERE id = %(i)s", {"i": lid})["status"] == "added"
    db.execute("DELETE FROM practice.inbound_leads WHERE id = %(i)s", {"i": lid})
    db.execute("DELETE FROM practice.companies WHERE id = %(i)s", {"i": c["id"]})


def test_demo_guest_cannot_use_a_password():
    from kit.hub.auth import authenticate
    assert authenticate("guest@demo.invalid", "") is None


def test_demo_pages_show_the_live_demo_inside_the_site(site):
    client, _ = site
    r = client.get("/demo/distribution")
    assert r.status_code == 200 and '<iframe class="demo-frame" src="https://distribution.demo.sanfordoperations.com/guest"' in r.text
    assert "frame-src" in r.headers["content-security-policy"] and "https://distribution.demo.sanfordoperations.com" in r.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]          # nobody may frame the website itself
    assert client.get("/demo/not-an-industry").status_code == 404
    assert 'href="/demo/construction"' in client.get("/demo").text                   # the picker stays on the site


def test_only_demo_hubs_can_be_framed_and_only_by_the_website(monkeypatch):
    from kit.hub import app as hub_app
    monkeypatch.setattr(hub_app, "EMBED_FROM", [])
    h = hub_app.security_headers()
    assert h["X-Frame-Options"] == "DENY" and "frame-ancestors 'none'" in h["Content-Security-Policy"]
    monkeypatch.setattr(hub_app, "EMBED_FROM", ["https://sanfordoperations.com"])
    h = hub_app.security_headers()
    assert "X-Frame-Options" not in h and "frame-ancestors https://sanfordoperations.com;" in h["Content-Security-Policy"]


def test_home_shows_how_it_works_without_scripts_and_hides_the_demo(site):
    client, _ = site
    html = client.get("/").text
    from website.how import INDUSTRIES
    assert html.count('class="how-panel"') == len(INDUSTRIES) == 5
    assert html.count('name="how-industry"') == 5 and html.count(" checked") >= 1   # one industry picked by default
    assert "<script" not in html and "style=" not in html                          # the CSP allows neither
    assert 'href="/demo"' not in html and "/contact?interest=demo" in html          # demo is by request only
    assert "Disallow: /demo" in client.get("/robots.txt").text
