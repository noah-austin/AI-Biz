"""Agent tests with a fake Claude client: no API key or web access needed."""
import datetime as dt
import json
from zoneinfo import ZoneInfo

import pytest

import psycopg2.extras

from kit import db
from kit.agents import engine, tools as agent_tools
from kit.agents.registry import BY_KEY
from kit.practice import inbox
from tests.test_ai import Block, FakeClient, Resp, text, tool_use


@pytest.fixture
def clean():
    def wipe():
        db.execute("""TRUNCATE practice.agent_items, practice.agent_runs, practice.tasks, practice.time_entries,
                      practice.invoices, practice.activities, practice.engagements, practice.companies RESTART IDENTITY CASCADE""")
        db.execute("DELETE FROM core.ai_usage WHERE feature = 'agents'")
    wipe()
    yield
    wipe()


PROSPECT = {"company": "Acme Field Services", "website": "https://acme.example", "industry": "Field services",
            "size": "200 people", "city": "Tulsa", "state": "OK", "contact_title": "COO",
            "why_fit": "Six branches and a new Salesforce rollout.", "signals": ["Hiring a BI analyst"],
            "sources": ["https://acme.example/about"], "angle": "Branch reporting",
            "first_message": "Hi, saw the new branches..."}


def test_prospecting_run_creates_inbox_items(clean):
    fake = FakeClient([
        Resp("tool_use", [tool_use("company_exists", {"name": "Acme Field Services"}, "t1")]),
        Resp("tool_use", [tool_use("propose_prospect", PROSPECT, "t2")]),
        Resp("end_turn", [text("Found 1 prospect.")]),
    ])
    run_id = engine.run("bizdev", "find_prospects", client=fake)
    r = db.one("SELECT status, items_created, summary FROM practice.agent_runs WHERE id = %(i)s", {"i": run_id})
    assert r["status"] == "done" and r["items_created"] == 1 and "Found" in r["summary"]
    names = [t.get("name") for t in fake.calls[0]["tools"]]
    assert "web_search" in names and "web_fetch" in names
    fetch = next(t for t in fake.calls[0]["tools"] if t.get("name") == "web_fetch")
    assert "linkedin.com" in fetch["blocked_domains"]
    assert "never send" in fake.calls[0]["system"][0]["text"].lower()


def test_approve_prospect_then_send_message(clean):
    run_id = engine.start_run("bizdev", "find_prospects")
    agent_tools.run("propose_prospect", dict(PROSPECT), run_id, "bizdev")
    item = db.one("SELECT id FROM practice.agent_items WHERE kind = 'prospect'")["id"]
    nxt = inbox.decide(item, "approve")
    company = db.one("SELECT id, stage, source, next_step FROM practice.companies WHERE name = 'Acme Field Services'")
    assert nxt == f"/companies/{company['id']}" and company["source"] == "Agent research"
    msg = db.one("SELECT id FROM practice.agent_items WHERE kind = 'message' AND company_id = %(c)s", {"c": company["id"]})
    inbox.decide(msg["id"], "sent")
    assert db.one("SELECT stage FROM practice.companies WHERE id = %(c)s", {"c": company["id"]})["stage"] == "contacted"
    assert db.one("SELECT count(*) AS n FROM practice.activities WHERE company_id = %(c)s", {"c": company["id"]})["n"] == 1


def test_duplicates_and_sourceless_prospects_are_refused(clean):
    run_id = engine.start_run("bizdev", "find_prospects")
    agent_tools.run("propose_prospect", dict(PROSPECT), run_id, "bizdev")
    with pytest.raises(agent_tools.ToolError):
        agent_tools.run("propose_prospect", dict(PROSPECT), run_id, "bizdev")
    with pytest.raises(agent_tools.ToolError):
        agent_tools.run("propose_prospect", {**PROSPECT, "company": "Other Co", "sources": ["not-a-url"]}, run_id, "bizdev")


def test_daily_brief_drafts_messages_for_follow_ups(clean):
    db.execute("""INSERT INTO practice.companies (name, stage, next_step, next_step_date)
                  VALUES ('Beta Co', 'conversation', 'Follow up', core.local_today())""")
    fake = FakeClient([
        Resp("tool_use", [tool_use("practice_overview", {}, "a"), tool_use("company_history", {"name": "Beta Co"}, "b")]),
        Resp("tool_use", [tool_use("propose_message", {"company": "Beta Co", "channel": "email", "body": "Hi again"}, "c"),
                          tool_use("write_brief", {"title": "Your Thursday", "body": "- Follow up with Beta Co"}, "d")]),
        Resp("end_turn", [text("Brief written.")]),
    ])
    engine.run("chief", "daily_brief", client=fake)
    kinds = sorted(r["kind"] for r in db.query("SELECT kind FROM practice.agent_items"))
    assert kinds == ["brief", "message"]
    results = fake.calls[1]["messages"][-1]["content"]
    assert all(not r["is_error"] for r in results) and "Beta Co" in results[1]["content"]


def test_run_cost_limit_stops_a_run(clean, monkeypatch):
    job = BY_KEY["social"].job("weekly_posts")
    monkeypatch.setattr(job, "run_cap_usd", 0.000001)
    fake = FakeClient([Resp("tool_use", [tool_use("recent_items", {}, f"x{i}")]) for i in range(5)])
    run_id = engine.run("social", "weekly_posts", client=fake)
    assert "limit" in db.one("SELECT summary FROM practice.agent_runs WHERE id = %(i)s", {"i": run_id})["summary"]
    assert len(fake.calls) == 1


def test_schedule_picks_due_jobs_once(clean):
    tz = ZoneInfo("America/Chicago")
    monday_8am = dt.datetime(2026, 10, 19, 8, 0, tzinfo=tz)
    due = engine.due_jobs(monday_8am)
    assert ("bizdev", "find_prospects") in due and ("social", "weekly_posts") in due and ("chief", "weekly_review") in due
    tuesday_5am = dt.datetime(2026, 10, 20, 5, 0, tzinfo=tz)
    assert engine.due_jobs(tuesday_5am) == []


def test_posts_never_mention_clients_rule_is_in_prompt():
    assert "never name or hint at a client" in BY_KEY["social"].job("weekly_posts").instructions.lower()


def test_a_dismissed_item_can_be_restored_with_a_corrected_draft(clean):
    with db.connect() as conn:
        item = db.one("""INSERT INTO practice.agent_items (agent, kind, title, body, data)
                         VALUES ('bizdev', 'prospect', 'Restore Test Co', '', %(d)s) RETURNING id""",
                      {"d": psycopg2.extras.Json({"company": "Restore Test Co", "first_message": "old wording"})}, conn=conn)["id"]
    inbox.decide(item, "dismiss")
    assert inbox.restore(item, "new wording") == f"/inbox#item-{item}"
    row = db.one("SELECT status, data FROM practice.agent_items WHERE id = %(i)s", {"i": item})
    assert row["status"] == "pending" and row["data"]["first_message"] == "new wording"
    assert inbox.restore(item) is None                     # only dismissed items come back


def test_signals_sent_as_text_still_show_as_a_list():
    assert inbox.as_list("Acquired X in 2026; 20+ sites\n- New ERP") == ["Acquired X in 2026", "20+ sites", "New ERP"]
    assert inbox.as_list(["a", " b "]) == ["a", "b"] and inbox.as_list(None) == []
