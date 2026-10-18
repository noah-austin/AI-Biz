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
EXPLAINER = (HERE / "explainer.html").read_text()  # built by website/brand/animation/build.py


@lru_cache
def cfg() -> dict:
    import os
    c = tomllib.loads((HERE / "config.toml").read_text())
    if os.environ.get("SITE_DEMO_URL"):  # for local testing
        c["demo_url"] = os.environ["SITE_DEMO_URL"]
    return c


def esc(v) -> str:
    return html.escape("" if v is None else str(v), quote=True)


NAV = [("/", "Home"), ("/what-we-build", "What we build"), ("/about", "About"), ("/contact", "Contact")]


def layout(title: str, body: str, path: str = "/", description: str = "") -> str:
    c = cfg()
    nav = "".join(f'<a href="{href}"{" aria-current=page" if href == path else ""}>{esc(label)}</a>' for href, label in NAV)
    desc = description or (f"{c['name']} brings a company's data together in one place, then builds the dashboards, "
                           "tools and AI agents it makes possible. For small and mid-size companies in any industry.")
    page_title = f"{title} | {c['name']}" if title != c["name"] else c["name"]
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(page_title)}</title><meta name="description" content="{esc(desc)}">
<meta property="og:title" content="{esc(page_title)}"><meta property="og:description" content="{esc(desc)}">
<link rel="icon" href="/static/brand/mark.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="/static/brand/apple-touch-icon.png"><meta property="og:image" content="{esc(c["url"])}/static/brand/profile-800.png"><meta property="og:url" content="{esc(c["url"])}{esc(path)}"><link rel="canonical" href="{esc(c["url"])}{esc(path)}"><link rel="stylesheet" href="/static/site.css">
</head><body>
<header class="site-head"><div class="wrap">
  <a class="logo" href="/" aria-label="{esc(c["name"])}, home"><picture><source srcset="/static/brand/lockup-reversed.svg" media="(prefers-color-scheme: dark)"><img src="/static/brand/lockup.svg" alt="{esc(c["name"])}" width="262" height="64"></picture></a>
  <nav aria-label="Main">{nav}</nav>
  <a class="btn small" href="/contact?interest=call">Book a call</a>
</div></header>
<main>{body}</main>
<footer class="site-foot"><div class="wrap">
  <div class="foot-grid">
    <div class="foot-brand"><a class="logo" href="/" aria-label="{esc(c["name"])}, home"><picture><source srcset="/static/brand/lockup-reversed.svg" media="(prefers-color-scheme: dark)"><img src="/static/brand/lockup.svg" alt="{esc(c["name"])}" width="262" height="64"></picture></a>
      <p>{esc(c["tagline"])}</p></div>
    <div><h4>Company</h4><a href="/what-we-build">What we build</a><a href="/about">About</a><a href="{esc(c["demo_url"])}">Live demo</a></div>
    <div><h4>Get in touch</h4><a href="/contact">Book a call</a><a href="mailto:{esc(c["email"])}">{esc(c["email"])}</a><span>{esc(c["city"])}</span></div>
  </div>
  <div class="foot-bottom"><span>© {date.today().year} {esc(c["name"])}</span><a href="/privacy">Privacy</a></div>
</div></footer>
</body></html>"""


def sec_head(eyebrow: str, title: str, lead: str = "", center: bool = True) -> str:
    return (f'<header class="sec-head{" center" if center else ""}"><p class="eyebrow">{esc(eyebrow)}</p>'
            f'<h2>{esc(title)}</h2>{f"<p class=lead>{esc(lead)}</p>" if lead else ""}</header>')


def cta_row(primary=("Book a call", "/contact?interest=call")) -> str:
    c = cfg()
    return (f'<div class="cta-row"><a class="btn" href="{primary[1]}">{esc(primary[0])}</a>'
            f'<a class="btn ghost" href="{esc(c["demo_url"])}">See a live demo →</a></div>')


FAQ = [
    ("Do we have to replace our systems?",
     "No. We connect to the systems you already use, read-only, and your team keeps working in them the same way. We add to what you have."),
    ("We already have Power BI or Tableau. Does this still help?",
     "Yes. Those tools are only as good as the data behind them. We build the trusted foundation underneath, and your existing dashboards can read from it too."),
    ("Is our data safe?",
     "We connect read-only, so nothing in your systems can be changed. It runs on a server in your company's name, or on a separate one we host just for you, with nightly backups, and each person sees only what they should. We sign a confidentiality agreement before any work starts, and the AI runs on business-grade services that don't train on your data."),
    ("How much does it cost?",
     "Every build is quoted to your company: how many systems we connect, how much data there is, and what we build on top. After our first conversations you get a written proposal with a fixed quote. A monthly plan then keeps it running."),
    ("How long does it take?",
     "It depends on the scope, and your proposal sets out the timeline. We work in stages, starting by reproducing the reports you already trust, so you see working results early."),
    ("Who looks after it once it's built?",
     "We do, on a monthly plan: monitoring, fixes, backups, and new tools and agents as you need them. Everything is documented, so you're never locked in."),
    ("Do we need a data team?",
     "No. That's the point. We are the data team you don't have to hire, and the tools are built for the people already running the business."),
]


def faq_html() -> str:
    items = "".join(f'<details class="faq"><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for q, a in FAQ)
    return f'<div class="faq-list">{items}</div>'


def home() -> str:
    c = cfg()
    gallery = [
        (v.mock_foundation(), "All your data in one place", "Every system connected into one database you own. Each number defined once."),
        (v.mock_scorecard(), "Reports that build themselves", "The weekly scorecard and monthly review, ready without anyone typing."),
        (v.mock_dashboard(), "Dashboards you can click into", "From the company total down to every record behind it."),
        (v.mock_tool(), "Tools that replace spreadsheets", "The forecast or tracker someone rebuilds every week, as a simple tool."),
        (v.mock_alerts(), "Alerts that come to you", "By email, Teams or phone, the moment something needs attention."),
        (v.mock_ask(), "AI that knows your business", "Plain-English questions, answered from your own data, with the numbers shown."),
    ]
    cards = "".join(f'<div class="show-card"><div class="show-visual">{m}</div><h3>{esc(t)}</h3><p>{esc(d)}</p></div>'
                    for m, t, d in gallery)
    steps = [("chat", "A conversation", "How you run, where your data lives, what you want."),
             ("doc", "A custom proposal", "A written plan and a fixed quote."),
             ("blocks", "We build it", "Data in one place, reports matched to the cent, then the tools."),
             ("refresh", "Run & Grow", "We keep it running and add what's next, every month.")]
    step_html = "".join(f'<li><span class="step-ico">{v.icon(i)}</span><small>Step {n}</small><h3>{t}</h3><p>{d}</p></li>'
                        for n, (i, t, d) in enumerate(steps, 1))
    why = [("people", "Operators, not a vendor", "We come from running companies, as COO and chief of staff."),
           ("blocks", "Built around you", "No off-the-shelf package. Nothing you use gets replaced."),
           ("server", "Your data, your choice", "Your own server or hosted by us. No per-seat licenses."),
           ("shield", "Safe by design", "Read-only access, nightly backups, and everyone sees only what they should.")]
    why_html = "".join(f'<div class="why">{v.icon(i)}<h3>{t}</h3><p>{d}</p></div>' for i, t, d in why)
    body = f"""
<section class="hero"><div class="wrap hero-grid">
  <div class="hero-copy">
    <p class="eyebrow">For leaders of small and mid-size companies</p>
    <h1>{esc(c["tagline"])}</h1>
    <p class="lead">We connect the systems your company runs on into one place, then build what that makes possible:
    reports that build themselves, tools, AI, and AI agents that do real work.</p>
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

<section class="explainer-section"><div class="wrap">
  {sec_head("In 24 seconds", "What we do", "Your systems come together in your data hub, so they work as one. Then we build reports, tools and AI on top.")}
  <link rel="stylesheet" href="/static/explainer.css">
  {EXPLAINER}
</div></section>

<section class="band"><div class="wrap">
  {sec_head("The difference", "From scattered to one place", "Most companies already have the data. It's just spread across systems that don't talk to each other.")}
  {v.before_after()}
</div></section>

<section><div class="wrap">
  {sec_head("What we build", "One foundation, everything on top", "Every build is custom. These are the pieces we put together for you.")}
  <div class="show-grid">{cards}</div>
  <p class="fine center">Examples use made-up data.</p>
</div></section>

<section class="agents-band"><div class="wrap">
  {sec_head("AI agents", "A day with your agents", "AI assistants with a job. They work from your data every day and hand the result to the right person.")}
  {v.agent_day()}
  <p class="approve-note">{v.icon("lock")}<span>Agents prepare the work. A person approves anything that goes out.</span></p>
</div></section>

<section><div class="wrap">
  {sec_head("How it works", "Four steps, no surprises")}
  <ol class="flow-steps">{step_html}</ol>
</div></section>

<section class="band"><div class="wrap demo-split">
  <div class="demo-copy">
    <p class="eyebrow">See it working</p>
    <h2>Explore a live example</h2>
    <p class="lead">A fictional company with realistic data: the scorecard, pipeline, win/loss, receivables and the AI assistant. No sign-up needed.</p>
    <a class="btn" href="{esc(c["demo_url"])}">Open the live demo →</a>
  </div>
  <div class="demo-shot">{v.demo_shot("home", "The demo hub's home page: bookings, win rate, pipeline, billing and cash, with a bookings-by-month chart.")}
  <p class="fine">Shown in the demo company's colors. Your hub uses yours.</p></div>
</div></section>

<section><div class="wrap">
  {sec_head("Why us", "Why work with us")}
  <div class="why-grid">{why_html}</div>
</div></section>

<section class="band"><div class="wrap narrow">
  {sec_head("Questions", "What people usually ask")}
  {faq_html()}
</div></section>

<section class="offer"><div class="wrap narrow center">
  <p class="eyebrow">Now taking a small number of founding clients</p>
  <h2>Start with a conversation</h2>
  <p class="lead">Tell us how your company runs and where your data lives. If there's a fit, you'll get a custom proposal.</p>
  <div class="cta-row center"><a class="btn" href="/contact?interest=call">Book a call</a><a class="btn ghost light" href="/what-we-build">What we build</a></div>
</div></section>"""
    return layout(c["name"], body, "/")


def what_we_build() -> str:
    agents = [("agent", "Daily brief", "For each leader: what changed and what needs attention today."),
              ("doc", "Reports drafted", "The weekly update or monthly review, written from your numbers."),
              ("calendar", "Meeting prep", "History and numbers on one page before a customer or board meeting."),
              ("bell", "Follow-up watch", "Deals gone quiet, invoices going late, work slipping, flagged to the owner."),
              ("search", "Research", "For example, new companies that look like your best customers.")]
    agent_html = "".join(f'<div class="agent-row">{v.icon(i)}<div><h3>{t}</h3><p>{d}</p></div></div>' for i, t, d in agents)
    factors = [("blocks", "Systems we connect"), ("db", "How much data"), ("chart", "What we build on top")]
    factor_html = "".join(f'<li>{v.icon(i)}{t}</li>' for i, t in factors)
    body = f"""
<section class="hero slim with-cta"><div class="wrap">
  <p class="eyebrow">What we build</p>
  <h1>Your data in one place, put to work</h1>
  <p class="lead">Every build is custom. These are the pieces we put together, on top of the systems you already use.</p>
  {cta_row()}
</div></section>

<section><div class="wrap">
  <div class="split">
    <div>
      <p class="eyebrow">The foundation</p>
      <h2>Your data hub</h2>
      <p>We connect every system with data in it into one database that you own. It updates on its own and keeps history.
      Every number is defined once, in plain English, so it means the same thing everywhere.</p>
      <p>Before showing you anything new, we reproduce the reports you already use, to the cent.</p>
    </div>
    {v.mock_foundation()}
  </div>
  <h3 class="sys-title">We connect anything with data in it</h3>
  {v.systems_grid()}
</div></section>

<section class="band"><div class="wrap">
  {sec_head("Reports and tools", "What your team uses every day")}
  <div class="show-grid">
    <div class="show-card"><div class="show-visual">{v.mock_scorecard()}</div><h3>A scorecard that fills itself in</h3><p>The weekly numbers leadership runs on.</p></div>
    <div class="show-card"><div class="show-visual">{v.mock_dashboard()}</div><h3>Dashboards and drill-downs</h3><p>By location, team or person, down to every record.</p></div>
    <div class="show-card"><div class="show-visual">{v.mock_tool()}</div><h3>Tools that replace spreadsheets</h3><p>Forecasts, trackers and workbooks, on live data.</p></div>
  </div>
</div></section>

<section><div class="wrap">
  <div class="split">
    {v.mock_ask()}
    <div>
      <p class="eyebrow">AI</p>
      <h2>AI that knows your business</h2>
      <ul class="checks">
        <li><strong>Ask in plain English,</strong> with the numbers shown so you can check them.</li>
        <li><strong>Insights:</strong> what changed this week and why.</li>
        <li><strong>Your other AI tools, connected:</strong> Copilot, ChatGPT or Claude can use the same data, read-only.</li>
      </ul>
    </div>
  </div>
</div></section>

<section class="agents-band"><div class="wrap">
  {sec_head("AI agents", "Agents that do the work", "AI assistants with a job, working from your data every day.")}
  <div class="split agents-split">
    {v.mock_brief()}
    <div class="agent-list">{agent_html}</div>
  </div>
  <p class="approve-note">{v.icon("lock")}<span>Agents prepare the work. A person approves anything that goes out.</span></p>
</div></section>

<section><div class="wrap">
  <div class="split even">
    <div>
      <p class="eyebrow">Pricing</p>
      <h2>How it's priced</h2>
      <p>Each build is quoted to your company. After our first conversations you get a written proposal with a fixed
      quote, then a monthly plan keeps it running and adds what's next.</p>
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
  <p class="eyebrow">Now taking a small number of founding clients</p>
  <h2>Let's talk about your company</h2>
  <p class="lead">A short conversation, then a custom proposal with a fixed quote.</p>
  <div class="cta-row center"><a class="btn" href="/contact?interest=call">Book a call</a><a class="btn ghost light" href="{esc(cfg()["demo_url"])}">See a live demo →</a></div>
</div></section>"""
    return layout("What we build", body, "/what-we-build",
                  "All your company's data in one place, with reports, tools, AI and AI agents built on top. Custom to your business.")


def about() -> str:
    c = cfg()
    principles = [("blocks", "The business first", "We start from how you run the company, not from the technology."),
                  ("check", "Your numbers first", "We reproduce the reports you already use, to the cent, before building anything new."),
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
    <p>We come from business operations, as COO and chief of staff: the people responsible for the numbers a company
    runs on. We've lived with data spread across a CRM, an accounting system and a pile of spreadsheets, with reports
    rebuilt by hand every week. We've also seen what changes once it's all in one place: tools, reports and AI that
    weren't possible while everything was scattered.</p>
    <p>Most companies don't need more software. They need a foundation that connects what they already have, and someone
    who understands how the business runs to build on it.</p>
    <p>We work with companies in any industry, across the US, that run on several systems and don't have a data team of
    their own. {esc(c["name"])} was founded by {esc(c["owner"])}.</p>
  </div>
  <div class="about-seal"><picture><source srcset="/static/brand/seal-reversed.svg" media="(prefers-color-scheme: dark)"><img src="/static/brand/seal.svg" alt="" width="280" height="280"></picture></div>
</div></section>
<section class="band"><div class="wrap">
  {sec_head("How we work", "Four things we hold to")}
  <div class="why-grid">{p_html}</div>
</div></section>
<section class="offer"><div class="wrap narrow center">
  <p class="eyebrow">Now taking a small number of founding clients</p>
  <h2>Let's talk about your company</h2>
  <p class="lead">A short conversation, then a custom proposal with a fixed quote.</p>
  <div class="cta-row center"><a class="btn" href="/contact?interest=call">Talk to us</a><a class="btn ghost light" href="{esc(c["demo_url"])}">See a live demo →</a></div>
</div></section>"""
    return layout("About", body, "/about")


SIZES = ["1–19 people", "20–49", "50–199", "200–499", "500–1,000", "Over 1,000"]
INTERESTS = [("call", "A call about my company"), ("demo", "A walkthrough of the demo"),
             ("partner", "Referral partnership"), ("other", "Something else")]


def contact(token: str, values: dict | None = None, errors: dict | None = None) -> str:
    c = cfg()
    v, e = values or {}, errors or {}

    def err(k):
        return f'<span class="field-err">{esc(e[k])}</span>' if k in e else ""

    def sel(options, chosen):
        return "".join(f'<option value="{esc(val)}"{" selected" if val == chosen else ""}>{esc(label)}</option>'
                       for val, label in options)
    body = f"""
<section class="hero slim"><div class="wrap">
  <p class="eyebrow">Contact</p>
  <h1>Let's talk about your company</h1>
  <p class="lead">Tell us a little about your company and what you'd like help with. We reply within one business day.</p>
</div></section>
<section><div class="wrap contact-grid">
  <form method="post" action="/contact" class="contact-form" novalidate>
    {'<p class="form-err">Please fix the highlighted fields.</p>' if e else ""}
    <input type="hidden" name="token" value="{esc(token)}">
    <div class="hp" aria-hidden="true"><label>Leave this empty<input type="text" name="website" tabindex="-1" autocomplete="off"></label></div>
    <label><span>Your name <span class="req">*</span></span><input name="name" required maxlength="120" autocomplete="name" value="{esc(v.get("name"))}">{err("name")}</label>
    <label><span>Work email <span class="req">*</span></span><input type="email" name="email" required maxlength="200" autocomplete="email" value="{esc(v.get("email"))}">{err("email")}</label>
    <label>Company<input name="company" maxlength="160" autocomplete="organization" value="{esc(v.get("company"))}"></label>
    <label>Your role<input name="role" maxlength="120" value="{esc(v.get("role"))}" placeholder="e.g. COO"></label>
    <label>Company size<select name="company_size"><option value="">Choose…</option>{sel([(s, s) for s in SIZES], v.get("company_size"))}</select></label>
    <label>I'm interested in<select name="interest">{sel(INTERESTS, v.get("interest") or "call")}</select></label>
    <label class="wide">Main systems you use<input name="systems" maxlength="200" value="{esc(v.get("systems"))}" placeholder="e.g. HubSpot, QuickBooks, Procore, a lot of Excel"></label>
    <label class="wide">Anything you'd like us to know<textarea name="message" rows="5" maxlength="3000">{esc(v.get("message"))}</textarea>{err("message")}</label>
    <p class="small muted wide">By sending this you agree to be contacted about your enquiry. See the <a href="/privacy">privacy notice</a>.</p>
    <div class="wide"><button class="btn" type="submit">Send</button></div>
  </form>
  <aside class="contact-side">
    <h3>Prefer email?</h3><p><a href="mailto:{esc(c["email"])}">{esc(c["email"])}</a></p>
    <h3>What happens next</h3>
    <ol><li>We read your note and reply within one business day.</li><li>We have a conversation about how your company runs and where your data lives.</li>
    <li>If there's a fit, we send you a custom proposal.</li></ol>
    <h3>Want to look first?</h3><p><a href="{esc(c["demo_url"])}">Explore the live demo →</a></p>
  </aside>
</div></section>"""
    return layout("Contact", body, "/contact")


def thanks(name: str) -> str:
    body = f"""<section class="hero slim"><div class="wrap narrow">
<h1>Thanks, {esc(name.split()[0] if name else "")}.</h1>
<p class="lead">Your note is in. We'll reply within one business day.</p>
<p>In the meantime, you can <a href="{esc(cfg()["demo_url"])}">explore the live demo</a> or read about
<a href="/what-we-build">what we build</a>.</p></div></section>"""
    return layout("Thanks", body, "/contact")


def privacy() -> str:
    c = cfg()
    body = f"""<section class="hero slim"><div class="wrap"><h1>Privacy notice</h1></div></section>
<section><div class="wrap"><div class="prose">
<p><strong>What we collect.</strong> Only what you type into the contact form (name, email, company, role, company
size, the systems you use and your message), plus basic server logs. We keep a one-way scrambled version of your IP
address for a short time, only to block spam.</p>
<p><strong>Why.</strong> To reply to your enquiry and, if you ask us to, to work with you. Nothing else.</p>
<p><strong>Who sees it.</strong> Only {esc(c["name"])}. We don't sell, rent or share it, and we don't use advertising or
tracking cookies on this site.</p>
<p><strong>How long.</strong> Enquiries that don't turn into work are deleted within 24 months, or sooner if you ask.</p>
<p><strong>Your choices.</strong> Email <a href="mailto:{esc(c["email"])}">{esc(c["email"])}</a> to see, correct or delete
what we hold about you.</p>
<p><strong>Client data</strong> (for companies we work with) is covered by a separate confidentiality agreement signed
before any work starts.</p>
</div></div></section>"""
    return layout("Privacy", body, "/privacy")


def not_found() -> str:
    return layout("Not found", '<section class="hero slim"><div class="wrap"><h1>That page isn\'t here.</h1>'
                               '<p><a href="/">Go to the home page</a></p></div></section>')
