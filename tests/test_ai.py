"""AI layer tests. A fake Claude client plays back scripted responses, so these run with no API key."""
import json

import pytest

from kit import db
from kit.ai import chat, insights, render, tools, usage


class Block:
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def to_dict(self, mode="json"):
        return {k: v for k, v in self.__dict__.items()}


class Usage:
    def __init__(self, i=1000, o=200):
        self.input_tokens, self.output_tokens = i, o
        self.cache_read_input_tokens, self.cache_creation_input_tokens = 0, 0


class Resp:
    def __init__(self, stop, content):
        self.stop_reason, self.content, self.usage, self.model = stop, content, Usage(), "claude-opus-5-5"
        self._request_id = "req_test"


class FakeClient:
    def __init__(self, script):
        self.script, self.calls = list(script), []
        self.beta = self
        self.messages = self

    def create(self, **kw):
        self.calls.append(json.loads(json.dumps(kw, default=str)))
        return self.script.pop(0)


def tool_use(name, args, id_="tu_1"):
    return Block(type="tool_use", id=id_, name=name, input=args)


def text(t):
    return Block(type="text", text=t)


@pytest.fixture
def users():
    db.execute("DELETE FROM core.app_users WHERE email LIKE '%%@ai-test.invalid'")
    with db.connect() as conn:
        a = db.one("""INSERT INTO core.app_users (email, name, role) VALUES ('admin@ai-test.invalid', 'AI Admin', 'admin')
                      RETURNING id, name, role, branches""", conn=conn)
        m = db.one("""INSERT INTO core.app_users (email, name, role, branches)
                      VALUES ('mgr@ai-test.invalid', 'AI Manager', 'viewer', ARRAY['AUS-03'])
                      RETURNING id, name, role, branches""", conn=conn)
    yield a, m
    db.execute("DELETE FROM core.ai_usage WHERE user_id IN (%(a)s, %(m)s)", {"a": a["id"], "m": m["id"]})
    db.execute("DELETE FROM core.app_users WHERE email LIKE '%%@ai-test.invalid'")


def new_job(user, q="How did Austin do?"):
    cid, jid = chat.new_id(), chat.new_id()
    db.execute("INSERT INTO core.ai_conversations (id, user_id) VALUES (%(c)s, %(u)s)", {"c": cid, "u": user["id"]})
    db.execute("INSERT INTO core.ai_jobs (id, conversation_id, user_id, question) VALUES (%(j)s, %(c)s, %(u)s, %(q)s)",
               {"j": jid, "c": cid, "u": user["id"], "q": q})
    return cid, jid


def test_chat_runs_tools_and_saves_the_turn(users):
    _, mgr = users
    cid, jid = new_job(mgr)
    fake = FakeClient([Resp("tool_use", [tool_use("find_deals", {"status": "won", "limit": 5})]),
                       Resp("end_turn", [text("Austin won **$1.2M**.\n\nHow I counted: won deals.")])])
    chat.run_job(jid, cid, mgr, "How did Austin do?", "/", client=fake)
    job = chat.job_status(jid, mgr)
    assert job["status"] == "done" and "<strong>$1.2M</strong>" in job["answer_html"]
    # The tool result went back to the model, limited to the manager's branch.
    result = json.loads(fake.calls[1]["messages"][-1]["content"][0]["content"])
    assert result["deals"] and {d["branch"] for d in result["deals"]} == {"Austin"}
    # No SQL tool for a branch-limited user; fallbacks and caching are on.
    assert "run_sql" not in [t["name"] for t in fake.calls[0]["tools"]]
    assert fake.calls[0]["fallbacks"] == "default" and fake.calls[0]["system"][0]["cache_control"]
    saved = db.one("SELECT messages FROM core.ai_conversations WHERE id = %(c)s", {"c": cid})["messages"]
    assert [m["role"] for m in saved] == ["user", "assistant", "user", "assistant"]
    assert db.one("SELECT count(*) AS n FROM core.ai_usage WHERE user_id = %(u)s", {"u": mgr["id"]})["n"] == 2


def test_other_branch_request_comes_back_as_error(users):
    _, mgr = users
    cid, jid = new_job(mgr)
    fake = FakeClient([Resp("tool_use", [tool_use("find_deals", {"branch": "Dallas"})]),
                       Resp("end_turn", [text("You can only see Austin.")])])
    chat.run_job(jid, cid, mgr, "Show Dallas deals", client=fake)
    result = fake.calls[1]["messages"][-1]["content"][0]
    assert result["is_error"] and "only see" in result["content"]


def test_refusal_is_not_kept_in_the_thread(users):
    admin, _ = users
    cid, jid = new_job(admin)
    chat.run_job(jid, cid, admin, "?", client=FakeClient([Resp("refusal", [])]))
    assert chat.job_status(jid, admin)["status"] == "done"
    assert db.one("SELECT messages FROM core.ai_conversations WHERE id = %(c)s", {"c": cid})["messages"] == []


def test_step_limit_stops_runaway_loops(users):
    admin, _ = users
    cid, jid = new_job(admin)
    script = [Resp("tool_use", [tool_use("company_overview", {}, f"t{i}")]) for i in range(chat.MAX_STEPS)]
    chat.run_job(jid, cid, admin, "loop", client=FakeClient(script))
    assert "more steps" in chat.job_status(jid, admin)["answer_html"]


def test_monthly_cap_blocks_new_questions(users, monkeypatch):
    admin, _ = users
    monkeypatch.setattr(usage, "api_key", lambda f: "test-key")
    real = usage.ai_settings()
    monkeypatch.setattr(usage, "ai_settings", lambda: {**real, "chat_monthly_cap_usd": 0.001})
    db.execute("INSERT INTO core.ai_usage (feature, user_id, model, cost_usd) VALUES ('chat', %(u)s, 'x', 0.01)",
               {"u": admin["id"]})
    with pytest.raises(usage.CapReached):
        chat.start(admin, "How are we doing?", None)


def test_ask_needs_the_custom_header():
    from fastapi.testclient import TestClient
    from kit.hub.app import app
    from kit.passwords import hash_password
    db.execute("DELETE FROM core.app_users WHERE email = 'hdr@ai-test.invalid'")
    db.execute("INSERT INTO core.app_users (email, name, password_hash) VALUES ('hdr@ai-test.invalid', 'H', %(h)s)",
               {"h": hash_password("test-password-123")})
    c = TestClient(app)
    c.post("/login", data={"email": "hdr@ai-test.invalid", "password": "test-password-123"})
    assert c.post("/ai/ask", json={"question": "hi"}).status_code == 400
    assert c.get("/ai/status").json()["suggestions"]
    db.execute("DELETE FROM core.app_users WHERE email = 'hdr@ai-test.invalid'")


def test_insights_keep_only_checked_items(monkeypatch):
    monkeypatch.setattr(usage, "api_key", lambda f: "test-key")
    payload = {"insights": [
        {"headline": "Austin win rate up 6 points", "detail": "44% vs 38% last year.", "link": "/winloss", "link_label": "Win / loss"},
        {"headline": "Click here", "detail": "No figure here.", "link": "/", "link_label": "x"},
        {"headline": "Phish 1", "detail": "Go to 5 sites", "link": "https://evil.example", "link_label": "x"}]}
    before = db.one("SELECT count(*) AS n FROM core.ai_insights")["n"]
    fake = FakeClient([Resp("end_turn", [text(json.dumps(payload))])])
    assert insights.generate(force=True, client=fake) == 0
    assert db.one("SELECT count(*) AS n FROM core.ai_insights")["n"] == before + 1
    assert fake.calls[0]["output_config"]["format"]["type"] == "json_schema"
    assert insights.latest()[0]["headline"] == "Austin win rate up 6 points"
    db.execute("DELETE FROM core.ai_insights")


def test_answer_rendering_is_safe():
    out = render.to_html("[ok](/deals) [bad](https://evil.example) <img src=x onerror=alert(1)> **b**")
    assert '<a href="/deals">ok</a>' in out and "evil.example" not in out and "<img" not in out
    assert "<strong>b</strong>" in out


def test_sql_tool_is_read_only():
    for q in ["delete from rpt.deals", "select 1; select 2", "update core.settings set value = 1"]:
        with pytest.raises(tools.ToolError):
            tools.run_sql(q)
    with pytest.raises(tools.ToolError):
        tools.run_sql("select * from core.app_users")
    assert tools.run_sql("select count(*) as n from rpt.deals")["rows"][0]["n"] > 0
