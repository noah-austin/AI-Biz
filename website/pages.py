"""The website's pages. Words live here; the name and email come from website/config.toml."""
import html
try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).parent


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
    desc = description or (f"{c['name']} helps small and mid-size companies connect their CRM and accounting into one "
                           "trusted set of numbers, with dashboards, alerts and AI on top.")
    page_title = f"{title} | {c['name']}" if title != c["name"] else c["name"]
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(page_title)}</title><meta name="description" content="{esc(desc)}">
<meta property="og:title" content="{esc(page_title)}"><meta property="og:description" content="{esc(desc)}">
<link rel="icon" href="/static/icon.svg" type="image/svg+xml"><link rel="stylesheet" href="/static/site.css">
</head><body>
<header class="site-head"><div class="wrap">
  <a class="logo" href="/"><span class="mark" aria-hidden="true"></span>{esc(c["name"])}</a>
  <nav aria-label="Main">{nav}</nav>
  <a class="btn small" href="/contact?interest=call">Book a call</a>
</div></header>
<main>{body}</main>
<footer class="site-foot"><div class="wrap">
  <div><strong>{esc(c["name"])}</strong><br>{esc(c["tagline"])}</div>
  <div><a href="mailto:{esc(c["email"])}">{esc(c["email"])}</a><br>{esc(c["city"])}</div>
  <div><a href="/privacy">Privacy</a> · <a href="{esc(c["demo_url"])}">Live demo</a></div>
</div></footer>
</body></html>"""


def cta_row(primary=("Book a call", "/contact?interest=call")) -> str:
    c = cfg()
    return (f'<div class="cta-row"><a class="btn" href="{primary[1]}">{esc(primary[0])}</a>'
            f'<a class="btn ghost" href="{esc(c["demo_url"])}">See a live demo →</a></div>')


def home() -> str:
    c = cfg()
    body = f"""
<section class="hero"><div class="wrap">
  <p class="eyebrow">For COOs, CFOs and owners of growing companies</p>
  <h1>{esc(c["tagline"])}</h1>
  <p class="lead">We connect the systems you already have (your CRM, accounting, projects and spreadsheets) into one
  trusted set of numbers. Then we build the scorecard, dashboards, alerts and AI your team actually uses.</p>
  {cta_row()}
  <p class="small muted">Built by an operator, not a software vendor. Custom to your company, on a server you own.</p>
</div></section>

<section class="band"><div class="wrap">
  <h2>Sound familiar?</h2>
  <div class="grid four">
    <div class="pain"><strong>Monday is report day.</strong> Someone spends hours rebuilding the leadership numbers in Excel.</div>
    <div class="pain"><strong>Two meetings, two numbers.</strong> Sales and finance bring different figures, and half the meeting is spent on whose is right.</div>
    <div class="pain"><strong>The CRM says one thing.</strong> Accounting says another. Nobody is sure which to trust.</div>
    <div class="pain"><strong>AI that knows nothing about you.</strong> Copilot or ChatGPT can't answer a single question about your own business.</div>
  </div>
</div></section>

<section><div class="wrap">
  <h2>What we build</h2>
  <p class="section-lead">Everything sits on one foundation: your data, connected and defined once, so every number means the same thing everywhere.</p>
  <div class="grid two">
    <div class="feature"><h3>One trusted set of numbers</h3><p>Your systems copied hourly into one database you own, with every metric written down and agreed. We reproduce your existing reports to the cent before showing anything new.</p></div>
    <div class="feature"><h3>A scorecard that fills itself in</h3><p>Your weekly numbers, ready on Monday morning without anyone typing them. Every figure clicks through to the records behind it.</p></div>
    <div class="feature"><h3>Alerts and reports that come to you</h3><p>"A $400K deal slipped a quarter." "A customer just passed 90 days late." Scheduled reports and alerts by email or Teams, so nobody has to go looking.</p></div>
    <div class="feature"><h3>AI that knows your business</h3><p>Ask questions in plain English and get answers from your own data, with the numbers to check them. It reads; it never changes anything.</p></div>
  </div>
</div></section>

<section class="band"><div class="wrap">
  <h2>How it works</h2>
  <ol class="steps">
    <li><span>1</span><div><h3>A conversation</h3><p>We talk about how your company runs, which systems hold your data, and what you wish you could see and do.</p></div></li>
    <li><span>2</span><div><h3>A custom proposal</h3><p>A written plan and quote built around your systems, your data and the tools that matter most to you.</p></div></li>
    <li><span>3</span><div><h3>We build it</h3><p>Your data brought together in one place, your existing reports reproduced, then the tools and the AI built on top.</p></div></li>
    <li><span>4</span><div><h3>Run &amp; Grow</h3><p>We keep it running and accurate, add what you need next, and review it with your leadership every month.</p></div></li>
  </ol>
</div></section>

<section><div class="wrap">
  <h2>Why work with us</h2>
  <div class="grid two">
    <div class="feature"><h3>An operator, not a vendor</h3><p>I've been the COO and chief of staff sitting in the meeting with the wrong numbers. I build what I wanted then.</p></div>
    <div class="feature"><h3>Built around you</h3><p>No off-the-shelf package. We start from how your company actually runs and build the tools you need on top of the systems you already have.</p></div>
    <div class="feature"><h3>You own it</h3><p>It runs on a server in your name, for a few dollars a month. No per-seat licences, no lock-in, and everything is documented so anyone can take it over.</p></div>
    <div class="feature"><h3>Safe by design</h3><p>Read-only access to your systems, nightly backups, each person sees only what they should, and the AI can never change a record.</p></div>
  </div>
</div></section>

<section class="offer"><div class="wrap">
  <div>
    <p class="eyebrow">Getting started</p>
    <h2>Start with a conversation</h2>
    <p>Tell us how your company runs and where your data lives. If there's a fit, you'll get a custom proposal built around
    your systems and what you want to do with them.</p>
  </div>
  <div class="cta-col"><a class="btn" href="/contact?interest=call">Book a call</a>
  <a class="btn ghost light" href="/what-we-build">What we build</a></div>
</div></section>

<section class="demo-band"><div class="wrap">
  <h2>See it working</h2>
  <p>Explore a live hub for a fictional company with realistic data: the scorecard, the pipeline, win/loss, receivables
  and the AI assistant. No sign-up needed.</p>
  <a class="btn" href="{esc(c["demo_url"])}">Open the live demo →</a>
</div></section>"""
    return layout(c["name"], body, "/")


def what_we_build() -> str:
    body = f"""
<section class="hero slim"><div class="wrap">
  <p class="eyebrow">What we build</p>
  <h1>Your data in one place, and the tools to use it</h1>
  <p class="lead">Every company is different, so every build is custom. These are the pieces we put together for you,
  on top of the systems you already use.</p>
  {cta_row()}
</div></section>

<section><div class="wrap narrow">
  <h2>One place for your data</h2>
  <p>We connect your CRM, accounting, project tools and spreadsheets into one database that you own. It updates on its
  own, keeps history, and every number is defined once and written down, so it means the same thing everywhere.</p>

  <h2>Tools your team uses every day</h2>
  <ul class="checks">
    <li><strong>A scorecard that fills itself in:</strong> the weekly numbers leadership runs on, ready without anyone typing them.</li>
    <li><strong>Dashboards and drill-downs:</strong> from the company total down to every record behind it, by branch, team or person.</li>
    <li><strong>Tools that replace spreadsheets:</strong> the forecast, the tracker or the workbook someone rebuilds every week.</li>
    <li><strong>Reports and alerts that come to you:</strong> by email or Teams, when something needs attention.</li>
  </ul>

  <h2>AI that knows your business</h2>
  <ul class="checks">
    <li><strong>Ask in plain English:</strong> answers from your own data, with the numbers shown so you can check them.</li>
    <li><strong>Insights and drafts:</strong> what changed this week and why, monthly review write-ups, summaries.</li>
    <li><strong>Your other AI tools, connected:</strong> a secure, read-only link so Copilot, ChatGPT or Claude can use the same trusted data.</li>
  </ul>

  <h2>How it's priced</h2>
  <p>Each build is quoted to your company: how many systems we connect, how much data there is, and what we build on top.
  After our first conversations you get a written proposal with a fixed quote, so there are no surprises.</p>

  <h2>Your data</h2>
  <p>Read-only access to your systems, so we never change anything in them. It all runs on a server in your name, with
  nightly backups, and each person sees only what they should. We sign a confidentiality agreement before any work starts.</p>
  {cta_row()}
</div></section>"""
    return layout("What we build", body, "/what-we-build",
                  "One place for your company's data, with dashboards, tools and AI built on top. Custom to your business.")


def about() -> str:
    c = cfg()
    body = f"""
<section class="hero slim"><div class="wrap">
  <p class="eyebrow">About</p>
  <h1>Built by an operator, for operators</h1>
</div></section>
<section><div class="wrap narrow prose">
  <p>I'm {esc(c["owner"])}. I've spent my career in business operations, as a COO and chief of staff: the person
  responsible for the numbers leadership runs the company on.</p>
  <p>At my last company, the numbers lived in a CRM, an accounting system and a pile of spreadsheets. Every week someone
  rebuilt the leadership report by hand, and every meeting started with an argument about whose figure was right. So I
  connected the systems into one place, wrote down what every number meant, and built the tools on top: a weekly
  scorecard, a forecast that replaced a workbook, pipeline and win/loss views, and an AI assistant that answers
  questions from the real data, all on a server that costs a few dollars a month.</p>
  <p>Once the data was in one place, we could build on it: tools, alerts and AI that weren't possible while everything
  was scattered. That's what most companies are missing. Not more software, but a foundation to build on.</p>
  <p>Now I do this for other companies: small and mid-size businesses that run on a CRM and an accounting system, don't
  have a data team, and want numbers they can trust and AI that actually helps.</p>
  <h2>How I work</h2>
  <ul class="checks">
    <li><strong>Your numbers first.</strong> I reproduce the reports you already use, to the cent, before building anything new.</li>
    <li><strong>You own everything.</strong> Your server, your data and your documentation. No lock-in.</li>
    <li><strong>Plain English.</strong> You'll always know what changed, how it was checked, and what it costs.</li>
  </ul>
  {cta_row(("Talk to me", "/contact?interest=call"))}
</div></section>"""
    return layout("About", body, "/about")


SIZES = ["1–19 people", "20–49", "50–199", "200–499", "500–1,000", "Over 1,000"]
CRMS = ["Salesforce", "HubSpot", "Microsoft Dynamics", "Zoho", "Pipedrive", "Other", "No CRM yet"]
INTERESTS = [("call", "A call about my company"), ("demo", "A walkthrough of the demo"),
             ("partner", "Referral partnership"), ("other", "Something else")]


def contact(token: str, values: dict | None = None, errors: dict | None = None) -> str:
    c = cfg()
    v, e = values or {}, errors or {}

    def err(k):
        return f'<span class="field-err">{esc(e[k])}</span>' if k in e else ""

    def sel(name, options, chosen):
        return "".join(f'<option value="{esc(val)}"{" selected" if val == chosen else ""}>{esc(label)}</option>'
                       for val, label in options)
    body = f"""
<section class="hero slim"><div class="wrap">
  <p class="eyebrow">Contact</p>
  <h1>Let's talk about your numbers</h1>
  <p class="lead">Tell me a little about your company and what you'd like help with. I reply within one business day.</p>
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
    <label>Company size<select name="company_size"><option value="">Choose…</option>{sel("company_size", [(s, s) for s in SIZES], v.get("company_size"))}</select></label>
    <label>CRM<select name="crm"><option value="">Choose…</option>{sel("crm", [(s, s) for s in CRMS], v.get("crm"))}</select></label>
    <label class="wide">I'm interested in<select name="interest">{sel("interest", INTERESTS, v.get("interest") or "call")}</select></label>
    <label class="wide">Anything you'd like me to know<textarea name="message" rows="5" maxlength="3000">{esc(v.get("message"))}</textarea>{err("message")}</label>
    <p class="small muted wide">By sending this you agree to be contacted about your enquiry. See the <a href="/privacy">privacy notice</a>.</p>
    <div class="wide"><button class="btn" type="submit">Send</button></div>
  </form>
  <aside class="contact-side">
    <h3>Prefer email?</h3><p><a href="mailto:{esc(c["email"])}">{esc(c["email"])}</a></p>
    <h3>What happens next</h3>
    <ol><li>I read your note and reply within one business day.</li><li>We have a 20-minute call about your systems and numbers.</li>
    <li>If there's a fit, I send you a custom proposal.</li></ol>
    <h3>Want to look first?</h3><p><a href="{esc(c["demo_url"])}">Explore the live demo →</a></p>
  </aside>
</div></section>"""
    return layout("Contact", body, "/contact")


def thanks(name: str) -> str:
    body = f"""<section class="hero slim"><div class="wrap narrow">
<h1>Thanks, {esc(name.split()[0] if name else "")}.</h1>
<p class="lead">Your note is in. I'll reply within one business day.</p>
<p>In the meantime, you can <a href="{esc(cfg()["demo_url"])}">explore the live demo</a> or read about
<a href="/what-we-build">what we build</a>.</p></div></section>"""
    return layout("Thanks", body, "/contact")


def privacy() -> str:
    c = cfg()
    body = f"""<section class="hero slim"><div class="wrap"><h1>Privacy notice</h1></div></section>
<section><div class="wrap narrow prose">
<p><strong>What we collect.</strong> Only what you type into the contact form (name, email, company, role, company
size, CRM and your message), plus basic server logs. We keep a one-way scrambled version of your IP address for a short
time, only to block spam.</p>
<p><strong>Why.</strong> To reply to your enquiry and, if you ask us to, to work with you. Nothing else.</p>
<p><strong>Who sees it.</strong> Only {esc(c["owner"])}. We don't sell, rent or share it, and we don't use advertising or
tracking cookies on this site.</p>
<p><strong>How long.</strong> Enquiries that don't turn into work are deleted within 24 months, or sooner if you ask.</p>
<p><strong>Your choices.</strong> Email <a href="mailto:{esc(c["email"])}">{esc(c["email"])}</a> to see, correct or delete
what we hold about you.</p>
<p><strong>Client data</strong> (for companies we work with) is covered by a separate confidentiality agreement signed
before any work starts.</p>
</div></section>"""
    return layout("Privacy", body, "/privacy")


def not_found() -> str:
    return layout("Not found", '<section class="hero slim"><div class="wrap"><h1>That page isn\'t here.</h1>'
                               '<p><a href="/">Go to the home page</a></p></div></section>')
