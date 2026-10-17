"""Proactive insights for the home page, written a few times a day.

    python -m kit.ai.insights           # from cron, e.g. 7am, noon and 4pm
    python -m kit.ai.insights --force   # ignore the per-day limit

One model call: the data comes from the same tools the chat uses (company-wide
view), the answer comes back as structured JSON, and each insight is checked
before it's shown (it must contain a figure and link inside the hub).
"""
import argparse
import json
import re
import secrets
import sys

from .. import db, metrics
from . import prompts, render, tools, usage

SCHEMA = {
    "type": "object",
    "properties": {"insights": {"type": "array", "items": {
        "type": "object",
        "properties": {"headline": {"type": "string"}, "detail": {"type": "string"},
                       "link": {"type": "string"}, "link_label": {"type": "string"}},
        "required": ["headline", "detail", "link", "link_label"], "additionalProperties": False}}},
    "required": ["insights"], "additionalProperties": False,
}
COMPANY = {"id": None, "name": "Insights", "branches": None}


def gather() -> dict:
    t = metrics.today()
    year_ago = t.replace(year=t.year - 1) if not (t.month == 2 and t.day == 29) else t.replace(year=t.year - 1, day=28)
    calls = {
        "overview": ("company_overview", {}),
        "last_7_days": ("recent_changes", {"days": 7}),
        "scorecard": ("weekly_scorecard", {}),
        "pipeline_by_stage": ("open_pipeline", {"group_by": "stage"}),
        "pipeline_by_branch": ("open_pipeline", {"group_by": "branch"}),
        "results_by_branch_ytd": ("deal_results", {"start": f"{t.year}-01-01", "end": t.isoformat(), "group_by": "branch"}),
        "where_we_sell_best_12m": ("where_we_sell_best", {"start": year_ago.isoformat(), "end": t.isoformat(),
                                                          "rows": "segment", "columns": "deal_type"}),
        "receivables": ("receivables", {}),
        "data_problems": ("data_problems", {}),
    }
    return {key: json.loads(tools.run(name, args, COMPANY)) for key, (name, args) in calls.items()}


def valid(item: dict) -> bool:
    if not re.search(r"\d", item["headline"] + item["detail"]):
        return False
    if len(item["headline"]) > 120 or len(item["detail"]) > 400:
        return False
    link = item["link"]
    return link.startswith("/") and not link.startswith("//") and "\\" not in link


def generate(force=False, client=None) -> int:
    if not usage.is_configured("insights"):
        print("No API key for insights (ANTHROPIC_API_KEY_INSIGHTS); skipping.")
        return 0
    s = usage.ai_settings()
    today = db.one("""SELECT count(DISTINCT batch_id) AS n FROM core.ai_insights
                      WHERE created_at >= core.local_today()::timestamp AT TIME ZONE core.client_tz()""")["n"]
    if today >= int(s["insights_per_day"]) and not force:
        print(f"Already wrote {today} batches today; skipping.")
        return 0
    usage.check_caps("insights")
    data = gather()
    if client is None:
        import anthropic
        client = anthropic.Anthropic(api_key=usage.api_key("insights"), max_retries=2, timeout=300)
    response = client.beta.messages.create(
        model=s["model"], max_tokens=16000,
        system=[{"type": "text", "text": prompts.insights_system(), "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": f"Today is {metrics.today().isoformat()}. The data:\n"
                                              f"<data>\n{json.dumps(data, default=str)}\n</data>"}],
        thinking={"type": "adaptive"},
        output_config={"effort": s["insights_effort"], "format": {"type": "json_schema", "schema": SCHEMA}},
        betas=["server-side-fallback-2026-07-01"], fallbacks="default",
    )
    cost = usage.record("insights", None, response)
    if response.stop_reason == "refusal":
        print("The model declined; no insights written.")
        return 1
    text = next((b.text for b in response.content if b.type == "text"), "")
    items = [i for i in json.loads(text).get("insights", []) if valid(i)][:5]
    if not items:
        print("No insights passed the checks; nothing written.")
        return 1
    batch = secrets.token_hex(6)
    for n, i in enumerate(items):
        db.execute("""INSERT INTO core.ai_insights (batch_id, position, headline, detail, link, link_label)
                      VALUES (%(b)s, %(n)s, %(h)s, %(d)s, %(l)s, %(ll)s)""",
                   {"b": batch, "n": n, "h": i["headline"], "d": i["detail"], "l": i["link"], "ll": i["link_label"]})
    print(f"Wrote {len(items)} insights (cost ${cost:.3f}).")
    return 0


def latest() -> list[dict]:
    """The most recent batch, for the home page. Branch-limited users see the company view, so it's hidden for them."""
    rows = db.query("""SELECT headline, detail, link, link_label, created_at FROM core.ai_insights
                       WHERE batch_id = (SELECT batch_id FROM core.ai_insights ORDER BY created_at DESC LIMIT 1)
                       ORDER BY position""")
    for r in rows:
        r["detail_html"] = render.to_html(r["detail"])
    return rows


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Write the home page's AI insights.")
    p.add_argument("--force", action="store_true")
    sys.exit(generate(p.parse_args().force))
