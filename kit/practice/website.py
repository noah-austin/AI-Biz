"""Website visits: what the public website counted itself (practice.site_hits), shown on the hub's Website page,
in the morning brief and to the assistant. No cookies, no third parties: a visitor is a one-way code that changes daily."""
import datetime as dt

from .. import db
from ..hub import ui
from ..hub.ui import esc

HOW = {"visitors": "People, not page views: one person reading three pages on the same day counts once. The code that "
                   "tells visitors apart changes every day, so someone coming back tomorrow counts again.",
       "plays": "People who pressed play on the What we build video (it only loads when someone presses play).",
       "enquiries": "Contact form messages that arrived, from the hub's Inbox."}
LOCAL_DAY = "(at AT TIME ZONE core.client_tz())::date"


def stats(days: int = 30) -> dict:
    """Visitors per day, top pages and where people came from, over the last `days` days (today included)."""
    since = {"d": days - 1}
    window = f"{LOCAL_DAY} >= core.local_today() - %(d)s"   # today and the days - 1 before it
    daily = db.query(f"""SELECT {LOCAL_DAY} AS day, count(DISTINCT visitor) AS visitors, count(*) AS views
                         FROM practice.site_hits WHERE kind = 'view' AND {window} GROUP BY 1 ORDER BY 1""", since)
    by_day = {r["day"]: r for r in daily}
    today = db.one("SELECT core.local_today() AS t")["t"]
    series = [{"day": today - dt.timedelta(days=i), "visitors": int(by_day.get(today - dt.timedelta(days=i), {}).get("visitors", 0)),
               "views": int(by_day.get(today - dt.timedelta(days=i), {}).get("views", 0))} for i in range(days - 1, -1, -1)]

    def people(where, d):
        return int(db.one(f"""SELECT count(DISTINCT ({LOCAL_DAY}, visitor)) AS n FROM practice.site_hits
                              WHERE {where} AND {LOCAL_DAY} > core.local_today() - %(d)s""", {"d": d})["n"])
    pages = db.query(f"""SELECT path, count(DISTINCT ({LOCAL_DAY}, visitor)) AS visitors, count(*) AS views
                         FROM practice.site_hits WHERE kind = 'view' AND {window}
                         GROUP BY path ORDER BY visitors DESC, views DESC LIMIT 10""", since)
    sources = db.query(f"""SELECT CASE WHEN source IS NOT NULL THEN 'Your link: ' || source
                                       WHEN ref_host IS NULL THEN 'Direct or email app'
                                       ELSE regexp_replace(ref_host, '^(www|m|l|lm)\\.', '') END AS source,
                                  count(DISTINCT ({LOCAL_DAY}, visitor)) AS visitors
                           FROM practice.site_hits WHERE kind = 'view' AND {window}
                           GROUP BY 1 ORDER BY visitors DESC LIMIT 10""", since)
    enquiries = int(db.one("""SELECT count(*) AS n FROM practice.inbound_leads
                              WHERE (created_at AT TIME ZONE core.client_tz())::date > core.local_today() - %(d)s""", since)["n"])
    return {"days": days, "today": today, "series": series,
            "visitors_today": people("kind = 'view'", 1), "visitors_7d": people("kind = 'view'", 7),
            "visitors": people("kind = 'view'", days), "views": sum(s["views"] for s in series),
            "tour_plays": people("kind = 'tour_play'", days), "enquiries": enquiries,
            "yesterday": series[-2]["visitors"] if days >= 2 else 0, "pages": pages, "sources": sources}


def summary_line() -> str:
    """One line for the morning brief."""
    s = stats(30)
    return (f"Website: {s['yesterday']} visitors yesterday, {s['visitors_7d']} in the last 7 days"
            + (f", {s['tour_plays']} played the tour video (30 days)" if s["tour_plays"] else "") + ".")


def page(request):
    s = stats(30)
    tiles = "".join([
        ui.tile("Visitors today", str(s["visitors_today"]), f'{s["yesterday"]} yesterday', None, HOW["visitors"]),
        ui.tile("Last 7 days", str(s["visitors_7d"]), "visitors"),
        ui.tile("Last 30 days", str(s["visitors"]), f'{s["views"]} pages read'),
        ui.tile("Played the tour", str(s["tour_plays"]), "last 30 days", None, HOW["plays"]),
        ui.tile("Enquiries", str(s["enquiries"]), "last 30 days", "/inbox", HOW["enquiries"]),
    ])
    chart = ui.chart("visits", {"type": "bar", "format": "count", "labels": [ui.short_date(x["day"]) for x in s["series"]],
                                "datasets": [{"label": "Visitors", "data": [x["visitors"] for x in s["series"]], "color": "--series-1"}]},
                     height=220, label="Visitors per day, last 30 days")
    names = {"/": "Home", "/what-we-build": "What we build", "/about": "About", "/contact": "Contact", "/thanks": "Thanks (sent the form)",
             "/privacy": "Privacy", "/demo": "Demo picker"}
    page_rows = "".join(f'<tr><td>{esc(names.get(r["path"], r["path"]))}</td><td class="n">{r["visitors"]}</td><td class="n">{r["views"]}</td></tr>'
                        for r in s["pages"]) or '<tr><td colspan="3">No visits yet.</td></tr>'
    src_rows = "".join(f'<tr><td>{esc(r["source"])}</td><td class="n">{r["visitors"]}</td></tr>' for r in s["sources"]) \
        or '<tr><td colspan="2">No visits yet.</td></tr>'
    body = f"""<div class="tiles">{tiles}</div>
<section class="card"><div class="card-head"><h2>Visitors per day</h2><span class="meta">last 30 days</span></div>{chart}</section>
<div class="cols even">
  <section class="card"><h2>Most-read pages</h2><div class="scroll"><table class="data"><thead><tr><th>Page</th>
  <th class="n">Visitors</th><th class="n">Views</th></tr></thead><tbody>{page_rows}</tbody></table></div></section>
  <section class="card"><h2>Where visitors came from</h2><div class="scroll"><table class="data"><thead><tr><th>Source</th>
  <th class="n">Visitors</th></tr></thead><tbody>{src_rows}</tbody></table></div>
  <p class="meta">Links in emails usually show as "Direct or email app". To see clicks from your emails, link to
  sanfordoperations.com/?from=email: they show here as "Your link: email".</p></section>
</div>
<p class="meta">Counted by the website itself: no cookies, no third parties. Search engines and other bots are left out.</p>"""
    return ui.page(request, "Website", body, "Website", subtitle="Visits to sanfordoperations.com")
