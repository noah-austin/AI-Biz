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
    assert 'class="hub-diagram wide"' in html and 'class="hub-diagram tall"' in html and "style=" not in html  # the policy blocks inline styles
    assert html.count('class="faq"') == 8 and 'rel="canonical"' in html
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
    r2 = client.post("/contact", data=fast, follow_redirects=False)                          # sent too quickly: asked to resend
    r3 = client.post("/contact", data={**fast, "token": "forged"}, follow_redirects=False)  # bad token
    assert r1.status_code == 303 and r2.status_code == 400 and "Send once more" in r2.text and r3.status_code == 400
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


def test_home_hides_the_demo(site):
    client, _ = site
    html = client.get("/").text
    assert 'href="/demo"' not in html and "/contact?interest=demo" in html          # demo is by request only
    assert "Disallow: /demo" in client.get("/robots.txt").text


def test_home_plays_the_explainer_with_a_phone_cut(site):
    client, _ = site
    html = client.get("/").text
    assert 'class="explainer-video tall"' in html and 'class="explainer-video wide"' in html   # two videos: iPhones ignore <source media>
    for name in ("explainer-tall.mp4", "explainer-wide.mp4", "explainer-wide-end.jpg"):
        assert client.get(f"/static/video/{name}", headers={"Range": "bytes=0-9"}).status_code == 206   # iPhones need ranges


def test_search_engines_and_monitors(site):
    client, _ = site
    assert "Sitemap:" in client.get("/robots.txt").text
    sm = client.get("/sitemap.xml")
    assert sm.status_code == 200 and "/what-we-build</loc>" in sm.text and "/demo" not in sm.text
    head = client.head("/")
    assert head.status_code == 200 and head.text == ""                                  # uptime checks use HEAD
    html = client.get("/").text
    assert 'application/ld+json' in html and 'og-card.jpg' in html
    nf = client.get("/nope").text
    assert 'name="robots" content="noindex"' in nf and 'rel="canonical"' not in nf
    assert "Thanks." in client.get("/thanks").text                                          # no name: no stray comma


def test_form_errors_point_at_their_fields(site):
    client, site_app = site
    r = post(client, site_app, email="not-an-email")
    assert r.status_code == 400 and 'aria-invalid="true" aria-describedby="err-email" autofocus' in r.text


def test_what_we_build_offers_the_tour_video_on_request(site):
    client, _ = site
    html = client.get("/what-we-build").text
    assert html.count('class="overview-video') == 2 and 'preload="none"' in html and "autoplay" not in html.split('class="overview"')[1].split("</div>")[0]
    for name in ("tour-wide.mp4", "tour-tall.mp4", "tour-wide.jpg", "tour-tall.jpg"):
        assert client.get(f"/static/video/{name}").status_code == 200, name


def test_visits_are_counted_without_cookies_and_bots_are_left_out(site):
    import re as _re
    client, _ = site
    time.sleep(0.3)                                  # let counts from earlier tests finish saving
    db.execute("DELETE FROM practice.site_hits")
    person = {"user-agent": "Mozilla/5.0 (iPhone) Safari", "referer": "https://www.linkedin.com/feed/"}
    r = client.get("/what-we-build?from=linkedin", headers=person)
    assert "set-cookie" not in r.headers
    token = _re.search(r'src="/seen.gif\?t=([0-9a-f]{16})"', r.text).group(1)              # the page's invisible image
    assert client.get(f"/seen.gif?t={token}", headers=person).headers["content-type"] == "image/gif"
    headless = client.get("/about", headers={"user-agent": "Mozilla/5.0 (X11) Chrome"})      # never loads the image: not counted
    assert "seen.gif" in headless.text
    client.get("/", headers={"user-agent": "Googlebot/2.1"})                                   # a declared bot: not counted at all
    client.get("/static/video/tour-wide.mp4", headers={**person, "range": "bytes=0-1023"})    # pressed play on the tour
    client.get("/static/site.css", headers=person)                                             # files aren't visits
    client.get("/static/video/tour-wide.jpg", headers=person)                                  # nor is the video's poster
    for _ in range(60):
        if db.one("SELECT count(*) AS n FROM practice.site_hits")["n"] >= 4:
            break
        time.sleep(0.05)
    hits = db.query("SELECT kind, path, ref_host, source, visitor, token FROM practice.site_hits ORDER BY kind DESC, path")
    assert [(h["kind"], h["path"]) for h in hits] == [("view", "/about"), ("view", "/what-we-build"), ("tour_play", "/static/video/tour-wide.mp4"),
                                                      ("seen", "/seen.gif")]
    view = hits[1]
    assert view["ref_host"] == "www.linkedin.com" and view["source"] == "linkedin" and len(view["visitor"]) == 16 and view["token"] == token
    from kit.practice import website
    s = website.stats(30)
    assert s["visitors_today"] == 1 and s["tour_plays"] == 1 and [p["path"] for p in s["pages"]] == ["/what-we-build"]
    assert {r["source"] for r in s["sources"]} == {"Your link: linkedin"} and s["filtered"] == 1
    one = website.stats(1)                                   # today only
    assert one["visitors"] == 1 and one["pages"] and one["sources"]
    db.execute("DELETE FROM practice.site_hits")


def test_email_link_checkers_arriving_in_a_burst_are_not_counted():
    from kit.practice import website
    db.execute("DELETE FROM practice.site_hits")
    with db.connect() as conn:
        for n, minute in enumerate([0, 1, 2, 90]):          # three scanners on delivery, then one person an hour and a half later
            db.execute("""INSERT INTO practice.site_hits (at, kind, path, source, visitor, token) VALUES
                          (now() - interval '3 hours' + %(m)s * interval '1 minute', 'view', '/', 'email', %(v)s, %(t)s),
                          (now() - interval '3 hours' + %(m)s * interval '1 minute', 'seen', '/seen.gif', NULL, %(v)s, %(t)s)""",
                       {"m": minute, "v": f"v{n}", "t": f"{n:016x}"}, conn)
    s = website.stats(2)                                    # today and yesterday, so the test holds just after midnight too
    assert {r["source"]: r["visitors"] for r in s["sources"]} == {"Your link: email": 1} and s["filtered"] == 3
    db.execute("DELETE FROM practice.site_hits")
