"""The assistant's toolbox (bin/hub): reads, proposals, and the changes Noah asks for."""
import json

import pytest

from kit import assistant, db
from kit.agents import engine
from tests.test_agents import PROSPECT, clean  # noqa: F401  (fixture)


def call(name, args=None, **kw):
    return json.loads(assistant.run(name, args or {}, **kw))


@pytest.fixture
def no_settings():
    db.execute("DELETE FROM practice.settings")
    yield
    db.execute("DELETE FROM practice.settings")


def test_unknown_tool_and_bad_fields(clean):
    with pytest.raises(assistant.ToolError):
        call("drop_everything")
    with pytest.raises(assistant.ToolError, match="Unknown field"):
        call("add_task", {"title": "x", "priority": "high"})
    with pytest.raises(assistant.ToolError, match="Missing"):
        call("add_task", {})
    with pytest.raises(assistant.ToolError, match="must be one of"):
        call("add_company", {"name": "Acme", "stage": "married"})


def test_propose_then_approve_from_chat(clean):
    assert call("propose_prospect", PROSPECT) == {"ok": True}
    items = call("inbox")["items"]
    assert [i["kind"] for i in items] == ["prospect"] and items[0]["agent"] == "assistant"
    out = call("decide_item", {"id": items[0]["id"], "action": "approve"})
    assert out["link"].startswith("/companies/")
    assert db.one("SELECT stage FROM practice.companies WHERE name = 'Acme Field Services'")["stage"] == "lead"
    msg = [i for i in call("inbox")["items"] if i["kind"] == "message"]
    assert len(msg) == 1
    with pytest.raises(assistant.ToolError, match="can't be approved"):
        call("decide_item", {"id": msg[0]["id"], "action": "approve"})
    call("decide_item", {"id": msg[0]["id"], "action": "sent"})
    assert db.one("SELECT stage FROM practice.companies WHERE name = 'Acme Field Services'")["stage"] == "contacted"
    with pytest.raises(assistant.ToolError, match="No pending"):
        call("decide_item", {"id": msg[0]["id"], "action": "dismiss"})


def test_company_task_and_activity_changes(clean):
    out = call("add_company", {"name": "Bluebonnet Mechanical", "contact_name": "Dana Ruiz", "next_step_date": "2026-11-02"})
    with pytest.raises(assistant.ToolError, match="already in the hub"):
        call("add_company", {"name": "bluebonnet mechanical"})
    call("update_company", {"company": "Bluebonnet", "stage": "conversation", "add_note": "Met at the TXAM event."})
    call("update_company", {"company": "Bluebonnet", "add_note": "Wants a dashboard."})
    c = db.one("SELECT * FROM practice.companies WHERE id = %(i)s", {"i": out["id"]})
    assert c["stage"] == "conversation" and "TXAM" in c["notes"] and "dashboard" in c["notes"]
    with pytest.raises(assistant.ToolError, match="YYYY-MM-DD"):
        call("update_company", {"company": "Bluebonnet", "next_step_date": "next Tuesday"})
    with pytest.raises(assistant.ToolError, match="No company"):
        call("log_activity", {"company": "Nobody Inc", "kind": "call", "summary": "x"})
    call("log_activity", {"company": "Bluebonnet", "kind": "call", "summary": "Intro call, 30 min."})
    assert db.one("SELECT count(*) AS n FROM practice.activities WHERE company_id = %(i)s", {"i": out["id"]})["n"] == 1
    t = call("add_task", {"title": "Send proposal", "company": "Bluebonnet", "due_date": "2026-11-05"})
    assert db.one("SELECT created_by FROM practice.tasks WHERE id = %(i)s", {"i": t["id"]})["created_by"] == "assistant"
    call("complete_task", {"id": t["id"]})
    with pytest.raises(assistant.ToolError, match="No open task"):
        call("complete_task", {"id": t["id"]})


def test_ideal_client_set_by_chat_reaches_the_jobs(clean, no_settings):
    before = call("get_settings")["ideal_client"]
    new = "Texas construction and field-service firms with 50-500 people and several branches."
    out = call("set_setting", {"key": "ideal_client", "value": new})
    assert out["before"] == before and out["after"] == new
    system, _ = engine.brief("bizdev", "find_prospects")
    assert new in system
    with pytest.raises(assistant.ToolError):
        call("set_setting", {"key": "ideal_client", "value": "short"})
    call("set_setting", {"key": "prospects_per_run", "value": 5})
    assert "Find 5 new companies" in engine.brief("bizdev", "find_prospects")[1]
    with pytest.raises(assistant.ToolError):
        call("set_setting", {"key": "prospects_per_run", "value": 500})


def test_enquiry_from_chat(clean):
    db.execute("DELETE FROM practice.inbound_leads")
    db.execute("""INSERT INTO practice.inbound_leads (name, email, company, interest, message)
                  VALUES ('Pat Lee', 'pat@example.com', 'Lee Plumbing', 'call', 'Can we talk?')""")
    lead = call("inbox")["website_enquiries"][0]
    call("decide_enquiry", {"id": lead["id"], "action": "add"})
    assert db.one("SELECT status FROM practice.inbound_leads WHERE id = %(i)s", {"i": lead["id"]})["status"] == "added"
    db.execute("DELETE FROM practice.inbound_leads")
