"""The website's pages. Words live here; the name and email come from website/config.toml. Voice: "we"."""
import html
try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib
from datetime import date
from functools import lru_cache
from pathlib import Path


from . import visuals as v

HERE = Path(__file__).parent


@lru_cache
def cfg() -> dict:
    import os
    c = tomllib.loads((HERE / "config.toml").read_text())
    if os.environ.get("SITE_DEMO_URL"):  # for local testing
        c["demo_url"] = os.environ["SITE_DEMO_URL"]
    return c


def _version(name: str) -> str:
    """A short fingerprint of a static file, added to its link so browsers fetch it again whenever it changes."""
    import hashlib
    return hashlib.sha256((HERE / "static" / name).read_bytes()).hexdigest()[:10]


VIDEO = ([f"video/explainer-{cut}{end}" for cut in ("wide", "tall") for end in (".mp4", ".jpg", "-end.jpg")]
         + [f"video/tour-{cut}{end}" for cut in ("wide", "tall") for end in (".mp4", ".jpg")])
ASSET_V = {name: _version(name) for name in ("site.css", *VIDEO)}


def esc(v) -> str:
    return html.escape("" if v is None else str(v), quote=True)


NAV = [("/", "Home"), ("/what-we-build", "What we build"), ("/about", "About"), ("/contact", "Contact")]


def layout(title: str, body: str, path: str = "/", description: str = "", noindex: bool = False, extra_head: str = "") -> str:
    c = cfg()
    nav = "".join(f'<a href="{href}"{" aria-current=page" if href == path else ""}>{esc(label)}</a>' for href, label in NAV)
    desc = description or (f"{c['name']} brings a company's data together in one place, then builds the reports, "
                           "custom software and AI agents it makes possible.")
    page_title = f"{title} | {c['name']}" if title != c["name"] else f"{c['name']} | Data hub, reporting and custom software for mid-size companies"
    canonical = "" if noindex else f'<link rel="canonical" href="{esc(c["url"])}{esc(path)}">'
    fonts = "".join(f'<link rel="preload" href="/static/fonts/{f}" as="font" type="font/woff2" crossorigin>'
                    for f in ("inter-latin-var.woff2", "playfair-700.woff2"))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(page_title)}</title><meta name="description" content="{esc(desc)}">{'<meta name="robots" content="noindex">' if noindex else ''}
<meta property="og:title" content="{esc(page_title)}"><meta property="og:description" content="{esc(desc)}">
<link rel="icon" href="/static/brand/mark.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="/static/brand/apple-touch-icon.png"><meta property="og:type" content="website"><meta property="og:site_name" content="{esc(c["name"])}"><meta property="og:image" content="{esc(c["url"])}/static/brand/og-card.jpg"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="{esc(c["name"])}: {esc(c["tagline"])}"><meta name="twitter:card" content="summary_large_image"><meta property="og:url" content="{esc(c["url"])}{esc(path)}">{canonical}{fonts}{extra_head}<link rel="stylesheet" href="/static/site.css?v={ASSET_V["site.css"]}">
</head><body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-head"><div class="wrap">
  <a class="logo" href="/" aria-label="{esc(c["name"])}, home"><picture><source srcset="/static/brand/lockup-reversed.svg" media="(prefers-color-scheme: dark)"><img src="/static/brand/lockup.svg" alt="{esc(c["name"])}" width="262" height="64"></picture></a>
  <nav aria-label="Main">{nav}</nav>
  <a class="btn small" href="/contact?interest=call">Start a conversation</a>
</div></header>
<main id="main">{body}</main>
<footer class="site-foot"><div class="wrap">
  <div class="foot-grid">
    <div class="foot-brand"><a class="logo" href="/" aria-label="{esc(c["name"])}, home"><picture><source srcset="/static/brand/lockup-reversed.svg" media="(prefers-color-scheme: dark)"><img src="/static/brand/lockup.svg" alt="{esc(c["name"])}" width="262" height="64"></picture></a>
      <p>{esc(c["tagline"])}</p></div>
    <div><p class="foot-h">Company</p><a href="/what-we-build">What we build</a><a href="/about">About</a><a href="{esc(c["demo_url"])}">Request a live demo</a></div>
    <div><p class="foot-h">Get in touch</p><a href="/contact">Start a conversation</a><a href="mailto:{esc(c["email"])}">{esc(c["email"])}</a><span>{esc(c["city"])}</span></div>
  </div>
  <div class="foot-bottom"><span>© {date.today().year} {esc(c["name"])}</span><a href="/privacy">Privacy</a></div>
</div></footer>
</body></html>"""


def _org_jsonld() -> str:
    """Who we are, for search engines. A JSON data block, which the no-scripts policy allows (it never runs)."""
    import json
    c = cfg()
    data = {"@context": "https://schema.org", "@type": "ProfessionalService", "name": c["name"], "url": c["url"],
            "email": c["email"], "logo": f'{c["url"]}/static/brand/mark-512.png', "image": f'{c["url"]}/static/brand/og-card.jpg',
            "slogan": c["tagline"], "founder": {"@type": "Person", "name": c["owner"]},
            "areaServed": "US", "address": {"@type": "PostalAddress", "addressLocality": "Austin", "addressRegion": "TX", "addressCountry": "US"},
            "description": "Brings a company's data together in one place, then builds the reports, custom software and AI agents it makes possible."}
    return '<script type="application/ld+json">' + json.dumps(data).replace("<", "\\u003c") + "</script>"


def sec_head(eyebrow: str, title: str, lead: str = "", center: bool = True) -> str:
    return (f'<header class="sec-head{" center" if center else ""}"><p class="eyebrow">{esc(eyebrow)}</p>'
            f'<h2>{esc(title)}</h2>{f"<p class=lead>{esc(lead)}</p>" if lead else ""}</header>')


def explainer() -> str:
    """The explainer video (website/brand/animation/): a tall cut on phones, a wide one elsewhere; a still for reduced motion."""
    u = lambda name: f"/static/{name}?v={ASSET_V[name]}"
    label = ("Animation: a company's scattered systems come together in one data hub, "
             "then reports, tools, AI and AI agents are built on top.")
    # Two videos rather than <source media>, which iPhone Safari ignores; CSS shows the one that fits the screen.
    videos = "".join(
        f'<video class="explainer-video {cut}" autoplay muted loop playsinline controls preload="metadata" poster="{u(f"video/explainer-{cut}.jpg")}" '
        f'aria-label="{label}"><source src="{u(f"video/explainer-{cut}.mp4")}" type="video/mp4"></video>' for cut in ("wide", "tall"))
    return f"""<div class="explainer">
    {videos}
    <picture class="explainer-still"><source srcset="{u("video/explainer-tall-end.jpg")}" media="(max-width: 640px)">
      <img src="{u("video/explainer-wide-end.jpg")}" alt="Your data in one place. Numbers everyone trusts, put to work." loading="lazy"></picture>
  </div>"""


def overview_video() -> str:
    """The tour (website/brand/demo-video/combined.py): systems into one place, then the tools on a demo hub. Played on request, a tall cut on phones."""
    u = lambda name: f"/static/{name}?v={ASSET_V[name]}"
    label = "Video: a company's systems connected into one data hub, then a tour of the tools built on it: home page, weekly scorecard, Ask AI, alerts and AI agents."
    return '<div class="overview">' + "".join(
        f'<video class="overview-video {cut}" controls playsinline preload="none" poster="{u(f"video/tour-{cut}.jpg")}" '
        f'aria-label="{label}"><source src="{u(f"video/tour-{cut}.mp4")}" type="video/mp4"></video>' for cut in ("wide", "tall")) + "</div>"


def cta_row(primary=("Start a conversation", "/contact?interest=call"), secondary=("What we build →", "/what-we-build")) -> str:
    return (f'<div class="cta-row"><a class="btn" href="{primary[1]}">{esc(primary[0])}</a>'
            f'<a class="btn ghost" href="{secondary[1]}">{esc(secondary[0])}</a></div>')


FAQ = [
    ("Do we have to replace our systems?",
     "No. We connect to the systems you already use, read-only, and your team keeps working in them the same way. We add to what you have."),
    ("Is this a ready-made product?",
     "No. Everything is built for your company: the hub, the screens and every tool on it, with your rules and your names for things. If it runs on your data, we can build it, from a commission calculator to a warehouse manager, a job-costing tool or a customer portal."),
    ("We already have Power BI or Tableau. Does this still help?",
     "Yes. Those tools are only as good as the data behind them. We build the trusted foundation underneath, and your existing dashboards can read from it too."),
    ("Is our data safe?",
     "We connect read-only, so nothing in your systems can be changed. It runs on a server in your company's name, or on a separate one we host just for you, with nightly backups, and each person sees only what they should. We sign a confidentiality agreement before any work starts, and the AI runs on business-grade services that don't train on your data."),
    ("How much does it cost?",
     "Every build is quoted to your company: how many systems we connect, how much data there is, and what we build on top. After our first conversations you get a written proposal with a fixed quote. A monthly plan then keeps it running."),
    ("What does the first project look like?",
     "A conversation about how you run and where your data lives, then a written proposal with the scope, timeline and a fixed quote. We usually start with two or three systems and the reports you rely on most, so you see working results early, then add custom software and AI in stages."),
    ("How do you know the numbers are right?",
     "Before anything new goes live, we rebuild the reports you already trust and compare them line by line. Every difference is traced to its source and explained: a definition you agree on, or a record that needs fixing. Each number is then defined once, in plain English, and used the same way everywhere."),
    ("Who owns what you build?",
     "You own your data, the database it lives in, and everything built specifically for you, with its documentation. We keep the general toolkit we reuse across clients, and your hub keeps running on it whether or not we keep working together."),
    ("What happens if we stop working together?",
     "You keep everything: the database, your reports and tools, and the documentation to run them or hand them to someone else. We help with the handover, remove our access, and delete any copies of your data we hold."),
    ("Can you work with our IT team?",
     "Yes. We go through your security review, use the access they approve (read-only accounts wherever possible) and agree with them where the hub runs. They can see exactly what's connected and who can see what."),
    ("What if the AI gets something wrong?",
     "The AI answers only from your defined numbers and shows how it got each answer, so it's easy to check. Agents prepare work, and a person approves anything that goes out. If something looks off, we trace it, fix the definition or the data, and it stays fixed."),
    ("Who looks after it once it's built?",
     "We do, on a monthly plan: monitoring, fixes, backups, and new tools and agents as you need them. Everything is documented, so you're never locked in."),
    ("Do we need a data team?",
     "No. That's the point. We are the data team you don't have to hire, and the tools are built for the people already running the business."),
]


def services() -> list:
    """The three services, named the same everywhere (home, What we build, FAQ). All run on the data hub."""
    return [
        (v.mock_scorecard(), "Business intelligence", "Numbers everyone trusts",
         "Your systems connected and every number defined once, so reports build themselves and match everywhere.",
         ["Scorecards that fill themselves in", "Dashboards you can click into", "Forecasts and alerts"]),
        (v.mock_tool(), "Custom operational software", "Tools that fit how you work",
         "Replace the spreadsheets and workarounds that run the business, with software built on the same data.",
         ["Commission calculators", "Job costing and scheduling", "Approvals and dispatch"]),
        (v.mock_ask(), "AI & workflow automation", "Routine work, prepared for you",
         "AI that answers from your defined numbers, and agents that draft the routine work for a person to approve.",
         ["Questions in plain English", "Meeting briefs and weekly summaries", "Follow-up drafts for approval"]),
    ]


def foundation_bar() -> str:
    return (f'<div class="foundation-bar">{v.icon("db")}<p><strong>All three run on your data hub:</strong> every system '
            'connected into one database you own, updated on its own, with each number defined once.</p></div>')


def faq_html() -> str:
    items = "".join(f'<details class="faq"><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for q, a in FAQ)
    return f'<div class="faq-list">{items}</div>'


def home() -> str:
    c = cfg()
    cards = "".join(
        f'<div class="show-card service"><div class="show-visual">{m}</div><p class="eyebrow">{esc(name)}</p><h3>{esc(t)}</h3>'
        f'<p>{esc(d)}</p><ul class="checks">{"".join(f"<li>{esc(x)}</li>" for x in ex)}</ul></div>'
        for m, name, t, d, ex in services())
    steps = [("chat", "A conversation", "How you run, where your data lives, what you want."),
             ("doc", "A custom proposal", "A written plan and a fixed quote."),
             ("blocks", "We build it", "Data in one place, your reports matched line by line, then the tools."),
             ("refresh", "Monthly plan", "We keep it running and add what's next, every month.")]
    step_html = "".join(f'<li><span class="step-ico">{v.icon(i)}</span><small>Step {n}</small><h3>{t}</h3><p>{d}</p></li>'
                        for n, (i, t, d) in enumerate(steps, 1))
    why = [("people", "Operators, not a vendor", "Founded by an ex-Google operations leader who built Google Fiber's operations system."),
           ("blocks", "Built around you", "No off-the-shelf package. We build the software you need, around the systems you keep."),
           ("server", "Your data, your choice", "Your own server or hosted by us. No per-seat licenses."),
           ("shield", "Safe by design", "Read-only access, nightly backups, and everyone sees only what they should.")]
    why_html = "".join(f'<div class="why">{v.icon(i)}<h3>{t}</h3><p>{d}</p></div>' for i, t, d in why)
    body = f"""
<section class="hero"><div class="wrap hero-grid">
  <div class="hero-copy">
    <p class="eyebrow">For leaders of small and mid-size companies</p>
    <h1>{esc(c["tagline"])}</h1>
    <p class="lead">We connect the systems your company runs on into one place, then build what that makes possible:
    reports that build themselves, custom software for how you work, AI and AI agents that do real work.</p>
    {cta_row()}
    <ul class="trust">{"".join(f"<li>{v.icon('check')}{t}</li>" for t in ("Read-only access", "Your data stays yours", "Fixed quote up front"))}</ul>
  </div>
  {v.hub_diagram()}
</div></section>

<section class="who"><div class="wrap who-row">
  <p class="who-label">Who we work with</p>
  <div class="who-roles">{"".join(f'<span class="chip">{v.icon(i)}{t}</span>' for i, t in (("people", "COOs"), ("dollar", "CFOs"), ("blocks", "Owners &amp; presidents"), ("clipboard", "Operations leaders")))}</div>
  <p class="who-note">at companies of 20 to 1,000 people, in any industry, that run on several systems and don't have a data team.</p>
</div></section>

<section><div class="wrap">
  {sec_head("The problem", "Your data is everywhere. Your answers aren't.", "Most companies already have the data they need. It's spread across systems that don't talk to each other, so reports get rebuilt by hand and two meetings end up with two different numbers.")}
  {v.before_after()}
</div></section>

<section class="band explainer-section"><div class="wrap">
  {sec_head("What we do", "Bring it together, then put it to work", "We connect your systems into one data hub that you own. Then we build the reports, software and AI that weren't possible while everything was scattered. Here it is in under 30 seconds.")}
  {explainer()}
</div></section>

<section><div class="wrap">
  {sec_head("What we build", "Three services, one foundation", "Every build is custom: we put together the pieces that fit how you run.")}
  <div class="show-grid">{cards}</div>
  {foundation_bar()}
  <p class="fine center">Examples use made-up data. <a href="/what-we-build">See everything we build →</a></p>
</div></section>

<section><div class="wrap">
  {sec_head("How we work", "Four steps, no surprises", "From a first conversation to a hub that keeps growing with you.")}
  <ol class="flow-steps">{step_html}</ol>
</div></section>

<section><div class="wrap">
  {sec_head("Our approach", "Why work with us")}
  <div class="why-grid">{why_html}</div>
</div></section>

<section class="band"><div class="wrap narrow">
  {sec_head("Questions", "What people usually ask")}
  {faq_html()}
</div></section>

<section class="offer"><div class="wrap narrow center">
  <p class="eyebrow">Now taking a small number of founding clients, at a founding rate</p>
  <h2>Start with a conversation</h2>
  <p class="lead">Tell us how your company runs and where your data lives. If there's a fit, you'll get a custom proposal.</p>
  <div class="cta-row center"><a class="btn" href="/contact?interest=call">Start a conversation</a><a class="btn ghost light" href="/what-we-build">What we build →</a></div>
</div></section>"""
    return layout(c["name"], body, "/", extra_head=_org_jsonld())


def demos() -> str:
    """Pick a demo: one fictional company per industry, each a click away from signing in as a guest."""
    c = cfg()
    cards = "".join(
        f'<a class="demo-card" href="/demo/{esc(d["slug"])}">{v.icon(d.get("icon", "chart"))}'
        f'<p class="eyebrow">{esc(d["industry"])}</p><h2>{esc(d["company"])}</h2><p>{esc(d["blurb"])}</p>'
        f'<ul>{"".join(f"<li>{esc(s)}</li>" for s in d.get("shows", []))}</ul>'
        f'<span class="demo-go">Open this demo →</span></a>' for d in c.get("demos", []))
    body = f"""<section class="hero slim"><div class="wrap narrow center">
  <p class="eyebrow">Live demos</p><h1>Pick a company like yours</h1>
  <p class="lead">Each is a fictional company with realistic data in its own hub. No sign-up: click one and you're in.
  Every number opens the records behind it.</p>
</div></section>
<section><div class="wrap"><div class="demo-grid">{cards}</div>
  <p class="fine center spaced">Don't see your industry? The hub is built around your systems, whatever you do.
  <a href="/contact?interest=demo">Tell us about yours</a> and we'll show you what it would look like.</p>
</div></section>"""
    return layout("Live demos", body, "/demo", "Live demos of the Sanford Operations hub for different industries, with realistic fictional data.",
                  noindex=True)


def demo_view(slug: str) -> str | None:
    """One demo, shown inside the website: industry tabs, the live hub, and a way to book a call."""
    c = cfg()
    demos = c.get("demos", [])
    d = next((x for x in demos if x["slug"] == slug), None)
    if not d:
        return None
    tabs = "".join(f'<a href="/demo/{esc(x["slug"])}"{" aria-current=page" if x is d else ""}>{esc(x["industry"])}</a>' for x in demos)
    body = f"""<section class="demo-stage"><div class="wrap wide">
  <nav class="demo-tabs" aria-label="Demo industries">{tabs}</nav>
  <div class="demo-bar">
    <div><h1>{esc(d["company"])}</h1><p>{esc(d["blurb"])} A fictional company with made-up data: click anything.</p></div>
    <div class="demo-bar-actions"><a class="btn small" href="/contact?interest=demo">See it on your data</a>
      <a class="demo-full" href="{esc(d["url"])}" target="_blank" rel="noopener">Full screen ↗</a></div>
  </div>
  <iframe class="demo-frame" src="{esc(d["url"])}" title="Live demo: {esc(d["company"])}" loading="eager"
          referrerpolicy="strict-origin-when-cross-origin"></iframe>
</div></section>"""
    return layout(f'{d["industry"]} demo', body, "/demo", noindex=True, description=
                  f'A live demo of the Sanford Operations hub for {d["industry"].lower()}: {d["company"]}, a fictional company.')


def what_we_build() -> str:
    agents = [("agent", "Daily brief", "For each leader: what changed and what needs attention today."),
              ("doc", "Reports drafted", "The weekly update or monthly review, written from your numbers."),
              ("calendar", "Meeting prep", "History and numbers on one page before a customer or board meeting."),
              ("bell", "Follow-up watch", "Deals gone quiet, invoices going late, work slipping, flagged to the owner."),
              ("search", "Research", "For example, new companies that look like your best customers.")]
    agent_html = "".join(f'<div class="agent-row">{v.icon(i)}<div><h3>{t}</h3><p>{d}</p></div></div>' for i, t, d in agents)
    factors = [("blocks", "Systems we connect"), ("db", "How much data"), ("chart", "What we build on top")]
    factor_html = "".join(f'<li>{v.icon(i)}{t}</li>' for i, t in factors)
    receive = [("db", "Your data hub", "The agreed systems connected into one database you own, updating on its own."),
               ("book", "A rulebook for your numbers", "Every number defined in plain English, with the same definition in the code."),
               ("check", "Your reports, tied out", "The reports you already trust, rebuilt and matched line by line. Every difference traced and explained."),
               ("chart", "The tools in your proposal", "Reports, custom software or AI, with each person seeing only what they should."),
               ("doc", "Documentation and handover", "How it works and how to run it, so you're never locked in."),
               ("shield", "Monitoring and backups", "Nightly backups and a watch on every connection, on the monthly plan.")]
    receive_html = "".join(f'<div class="why">{v.icon(i)}<h3>{t}</h3><p>{d}</p></div>' for i, t, d in receive)
    body = f"""
<section class="hero slim with-cta"><div class="wrap">
  <p class="eyebrow">What we build</p>
  <h1>Your data in one place, put to work</h1>
  <p class="lead">Every build starts with your data hub. On it we deliver three services: business intelligence, custom
  operational software, and AI &amp; workflow automation, around the systems you already use. Nothing is one-size-fits-all.</p>
  {cta_row(secondary=("Request a live demo →", "/contact?interest=demo"))}
</div></section>

<section class="band"><div class="wrap">
  {sec_head("Take the tour", "See it come together", "Under a minute: how we connect your systems into one place, then the tools we build on it, shown on a demo company's hub.")}
  {overview_video()}
  <p class="fine center">Bluestem Facility Services is a fictional demo company with made-up data.</p>
</div></section>

<section><div class="wrap">
  <div class="split">
    <div>
      <p class="eyebrow">The foundation</p>
      <h2>Your data hub</h2>
      <p>We connect the systems your company runs on into one database that you own. It updates on its own and keeps history.
      Every number is defined once, in plain English, so it means the same thing everywhere.</p>
      <p>Before showing you anything new, we rebuild the reports you already use and match them line by line, with every difference explained. All three services below run on this.</p>
    </div>
    {v.mock_foundation()}
  </div>
  <h3 class="sys-title">Systems we connect</h3>
  {v.systems_grid()}
  <p class="fine center">Access depends on each system: some need a higher plan, an add-on or the vendor's approval, and a few
  work best through a scheduled export. We check this before we quote.</p>
</div></section>

<section class="band"><div class="wrap">
  {sec_head("Service 1 · Business intelligence", "Numbers everyone trusts", "Reports, dashboards and alerts built on the hub, so every number matches everywhere.")}
  <div class="show-grid">
    <div class="show-card"><div class="show-visual">{v.mock_scorecard()}</div><h3>A scorecard that fills itself in</h3><p>The weekly numbers leadership runs on.</p></div>
    <div class="show-card"><div class="show-visual">{v.mock_dashboard()}</div><h3>Dashboards and drill-downs</h3><p>By location, team or person, down to every record.</p></div>
    <div class="show-card"><div class="show-visual">{v.mock_alerts()}</div><h3>Forecasts and alerts</h3><p>The right person hears as soon as something needs attention.</p></div>
  </div>
  <p class="fine center">Examples use made-up data.</p>
</div></section>

<section><div class="wrap">
  <div class="split">
    {v.mock_commission()}
    <div>
      <p class="eyebrow">Service 2 · Custom operational software</p>
      <h2>Tools that fit how you work</h2>
      <p>This isn't a prebuilt dashboard. We build the software your team needs, on the same data: a commission
      calculator that follows your plan, a warehouse manager, a job-costing tool, a customer portal. Your rules, your
      workflow, your names for things. If it runs on your data, we can build it.</p>
      {v.custom_chips()}
    </div>
  </div>
</div></section>

<section class="band"><div class="wrap">
  <div class="split">
    <div>
      <p class="eyebrow">Service 3 · AI &amp; workflow automation</p>
      <h2>AI that knows your business</h2>
      <p>Because the data is clean and defined once, AI can answer from it and show its working.</p>
      <ul class="checks">
        <li><strong>Ask in plain English,</strong> with the numbers shown so you can check them.</li>
        <li><strong>Insights:</strong> what changed this week and why.</li>
        <li><strong>Your other AI tools, connected:</strong> Copilot, ChatGPT or Claude can use the same data, read-only.</li>
      </ul>
    </div>
    {v.mock_ask()}
  </div>
</div></section>

<section class="agents-band"><div class="wrap">
  {sec_head("AI & workflow automation · Agents", "Agents that do the work", "AI assistants, each with one job, working from your data every day.")}
  <div class="split agents-split">
    {v.mock_brief()}
    <div class="agent-list">{agent_html}</div>
  </div>
  <p class="approve-note">{v.icon("lock")}<span>Agents prepare the work. A person approves anything that goes out.</span></p>
</div></section>

<section><div class="wrap">
  {sec_head("What you receive", "What a first build delivers", "Your proposal lists exactly what's included. A typical first build gives you:")}
  <div class="receive-grid">{receive_html}</div>
  <div class="scope-cols">
    <div><h3>{v.icon("check")}Included in the fixed quote</h3><p>Everything listed in your proposal: the systems we connect,
    the reports we reproduce and tie out, the tools and AI we build, documentation and handover.</p></div>
    <div><h3>{v.icon("doc")}Quoted separately</h3><p>New systems, new tools, or larger changes beyond the monthly plan. Any
    fees a software vendor charges for access (a higher plan or an add-on) are yours, and we flag them before you sign.</p></div>
  </div>
</div></section>

<section class="band"><div class="wrap">
  <div class="split even">
    <div>
      <p class="eyebrow">Pricing</p>
      <h2>How it's priced</h2>
      <p>You don't have to start with all three services. Most companies start with the hub and the reports they already
      run, then add custom software and AI. Each build is quoted to your company: after our first conversations you get a
      written proposal with a fixed quote, then a monthly plan keeps it running and adds what's next.</p>
      <ul class="factors">{factor_html}</ul>
    </div>
    <div>
      <p class="eyebrow">Hosting</p>
      <h2>Where it runs</h2>
      <div class="host-grid">
        <div class="host">{v.icon("server")}<h3>Your server</h3><p>In your company's name. We manage it.</p></div>
        <div class="host">{v.icon("cloud")}<h3>Hosted by us</h3><p>Its own separate server, never shared.</p></div>
      </div>
      <p class="small muted">Either way: the data is yours, read-only access to your systems, nightly backups, and a
      confidentiality agreement before any work starts.</p>
    </div>
  </div>
</div></section>

<section class="offer"><div class="wrap narrow center">
  <p class="eyebrow">Now taking a small number of founding clients, at a founding rate</p>
  <h2>Let's talk about your company</h2>
  <p class="lead">A short conversation, then a custom proposal with a fixed quote.</p>
  <div class="cta-row center"><a class="btn" href="/contact?interest=call">Start a conversation</a><a class="btn ghost light" href="{esc(cfg()["demo_url"])}">Request a live demo →</a></div>
</div></section>"""
    return layout("What we build", body, "/what-we-build",
                  "All your company's data in one place, with three services built on it: business intelligence, custom operational software, and AI and workflow automation.")


def about() -> str:
    c = cfg()
    principles = [("blocks", "The business first", "We start from how you run the company, not from the technology."),
                  ("check", "Your numbers first", "We rebuild the reports you already use and match them line by line before building anything new."),
                  ("server", "You own everything", "Your data and your documentation, wherever it runs. No lock-in."),
                  ("chat", "Plain English", "You'll always know what changed, how it was checked, and what it costs.")]
    p_html = "".join(f'<div class="why">{v.icon(i)}<h3>{t}</h3><p>{d}</p></div>' for i, t, d in principles)
    body = f"""
<section class="hero slim"><div class="wrap">
  <p class="eyebrow">About us</p>
  <h1>Built by operators, for operators</h1>
  <p class="lead">{esc(c["name"])} helps small and mid-size companies bring their data together in one place and put it to work.</p>
</div></section>
<section><div class="wrap split about-split">
  <div class="prose">
    <p>{esc(c["name"])} was founded by {esc(c["owner"])}, an operations expert who spent five years as an operations
    leader at Google. There he built the operations system Google Fiber used to expand and deploy into new territories.</p>
    <p>We come from operations: the people responsible for the numbers a company runs on. We know what it's like when data
    is spread across a CRM, an accounting system and a pile of spreadsheets, with reports rebuilt by hand every week. And
    we've seen what changes once it's all in one place: tools, reports and AI that weren't possible while everything was
    scattered.</p>
    <p>Most companies don't need more software. They need a foundation that connects what they already have, and someone
    who understands how the business runs to build on it.</p>
    <p>We work from Austin, Texas, with companies in any industry across the US that run on several systems and don't
    have a data team of their own.</p>
  </div>
  <div class="about-seal"><picture><source srcset="/static/brand/seal-reversed.svg" media="(prefers-color-scheme: dark)"><img src="/static/brand/seal.svg" alt="" width="280" height="280"></picture></div>
</div></section>
<section class="band"><div class="wrap">
  {sec_head("How we work", "Four things we hold to")}
  <div class="why-grid">{p_html}</div>
</div></section>
<section class="offer"><div class="wrap narrow center">
  <p class="eyebrow">Now taking a small number of founding clients, at a founding rate</p>
  <h2>Let's talk about your company</h2>
  <p class="lead">A short conversation, then a custom proposal with a fixed quote.</p>
  <div class="cta-row center"><a class="btn" href="/contact?interest=call">Start a conversation</a><a class="btn ghost light" href="{esc(c["demo_url"])}">Request a live demo →</a></div>
</div></section>"""
    return layout("About", body, "/about", f"{c['name']} brings a company's data together in one place and puts it to work. Built by operators, for operators.")


SIZES = ["1–19 people", "20–49", "50–199", "200–499", "500–1,000", "Over 1,000"]
INTERESTS = [("call", "A call about my company"), ("demo", "A live demo"),
             ("partner", "Referral partnership"), ("other", "Something else")]


def contact(token: str, values: dict | None = None, errors: dict | None = None) -> str:
    c = cfg()
    vals, e = values or {}, errors or {}

    def err(k):
        return f'<span class="field-err" id="err-{k}">{esc(e[k])}</span>' if k in e else ""

    first = next((k for k in ("name", "email", "company", "message") if k in e), None)

    def inv(k):
        return (f' aria-invalid="true" aria-describedby="err-{k}"' + (" autofocus" if k == first else "")) if k in e else ""

    def sel(options, chosen):
        return "".join(f'<option value="{esc(val)}"{" selected" if val == chosen else ""}>{esc(label)}</option>'
                       for val, label in options)
    body = f"""
<section class="hero slim"><div class="wrap">
  <p class="eyebrow">Contact</p>
  <h1>Tell us how your company runs</h1>
  <p class="lead">Tell us a little about your company and what you'd like help with. We reply within one business day.</p>
</div></section>
<section><div class="wrap contact-grid">
  <form method="post" action="/contact" class="contact-form" novalidate>
    {f'<p class="form-err" role="alert">{esc(e.get("_form") or "Please fix the highlighted fields.")}</p>' if e else ""}
    <input type="hidden" name="token" value="{esc(token)}">
    <div class="hp" aria-hidden="true"><label>Leave this empty<input type="text" name="website" tabindex="-1" autocomplete="off"></label></div>
    <label><span>Your name <span class="req">*</span></span><input name="name" required maxlength="120" autocomplete="name"{inv("name")} value="{esc(vals.get("name"))}">{err("name")}</label>
    <label><span>Work email <span class="req">*</span></span><input type="email" name="email" required maxlength="200" autocomplete="email"{inv("email")} value="{esc(vals.get("email"))}">{err("email")}</label>
    <label><span>Company <span class="req">*</span></span><input name="company" required maxlength="160" autocomplete="organization"{inv("company")} value="{esc(vals.get("company"))}">{err("company")}</label>
    <label>I'm interested in<select name="interest">{sel(INTERESTS, vals.get("interest") or "call")}</select></label>
    <label class="wide">What would you like help with?<textarea name="message" rows="4" maxlength="3000"{inv("message")}>{esc(vals.get("message"))}</textarea>{err("message")}</label>
    <details class="wide more"{" open" if any(vals.get(k) for k in ("role", "company_size", "systems")) else ""}><summary>Tell us more (optional)</summary>
      <div class="more-fields">
        <label>Your role<input name="role" maxlength="120" value="{esc(vals.get("role"))}" placeholder="e.g. COO"></label>
        <label>Company size<select name="company_size"><option value="">Choose…</option>{sel([(s, s) for s in SIZES], vals.get("company_size"))}</select></label>
        <label class="wide">Main systems you use<input name="systems" maxlength="200" value="{esc(vals.get("systems"))}" placeholder="e.g. HubSpot, QuickBooks, Procore, a lot of Excel"></label>
      </div>
    </details>
    <p class="small muted wide">By sending this you agree to be contacted about your inquiry. See the <a href="/privacy">privacy notice</a>.</p>
    <div class="wide"><button class="btn" type="submit">Send</button></div>
  </form>
  <aside class="contact-side">
    <h2>Prefer email?</h2><p><a href="mailto:{esc(c["email"])}">{esc(c["email"])}</a></p>
    <h2>What happens next</h2>
    <ol><li>We read your note and reply within one business day.</li><li>We have a conversation about how your company runs and where your data lives.</li>
    <li>If there's a fit, we send you a custom proposal.</li></ol>
    <h2>Want to see it first?</h2><p>Choose "A live demo" in the form and we'll show you a live hub for a company like yours.</p>
  </aside>
</div></section>"""
    return layout("Contact", body, "/contact", "Tell us how your company runs and where your data lives. We reply within one business day.")


def thanks(name: str) -> str:
    body = f"""<section class="hero slim"><div class="wrap narrow">
<h1>{f"Thanks, {esc(name.split()[0][:40])}." if name.strip() else "Thanks."}</h1>
<p class="lead">Your note is in. We'll reply within one business day.</p>
<p>In the meantime, you can read about
<a href="/what-we-build">what we build</a>.</p></div></section>"""
    return layout("Thanks", body, "/thanks", noindex=True)


def privacy() -> str:
    c = cfg()
    body = f"""<section class="hero slim"><div class="wrap"><h1>Privacy notice</h1></div></section>
<section><div class="wrap"><div class="prose">
<p><strong>What we collect.</strong> Only what you type into the contact form (name, email, company, role, company
size, the systems you use and your message), plus basic server logs. We store a one-way scrambled version of your IP
address with your message, only to block spam; it can't be turned back into the address.</p>
<p><strong>Visit counts.</strong> To see how many people use the site, we count page visits without cookies: the page,
the site you came from, and a one-way code that changes every day, so it can't identify you or follow you from one day
to the next.</p>
<p><strong>Why.</strong> To reply to your inquiry and, if you ask us to, to work with you. Nothing else.</p>
<p><strong>Who sees it.</strong> Only {esc(c["name"])}, plus the companies that host this site and run our email,
which handle it on our behalf. We don't sell, rent or share it, and we don't use advertising or
tracking cookies on this site.</p>
<p><strong>How long.</strong> Inquiries that don't turn into work are deleted within 24 months, or sooner if you ask.</p>
<p><strong>Your choices.</strong> Email <a href="mailto:{esc(c["email"])}">{esc(c["email"])}</a> to see, correct or delete
what we hold about you.</p>
<p><strong>Client data</strong> (for companies we work with) is covered by a separate confidentiality agreement signed
before any work starts.</p>
</div></div></section>"""
    return layout("Privacy", body, "/privacy", f"How {c['name']} handles what you send through this website.")


def not_found() -> str:
    body = """<section class="hero slim not-found"><div class="wrap">
  <p class="eyebrow">404</p><h1>That page isn't here.</h1>
  <p class="lead">It may have moved, or the link has a typo. These are a good place to start:</p>
  <ul class="nf-links"><li><a href="/">Home</a></li><li><a href="/what-we-build">What we build</a></li>
  <li><a href="/about">About</a></li><li><a href="/contact">Contact</a></li></ul>
</div></section>"""
    return layout("Not found", body, "", noindex=True)
