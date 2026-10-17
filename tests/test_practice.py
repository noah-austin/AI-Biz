"""Practice app tests, against a scratch practice schema in the demo database."""
import datetime as dt

import pytest

from kit import db
from kit.hub import forms
from kit.practice import metrics as pm
from kit.practice import pages as pp


class Form(dict):
    def get(self, k, default=None):
        return super().get(k, default)


@pytest.fixture
def clean():
    def wipe():
        db.execute("""TRUNCATE practice.time_entries, practice.invoices, practice.expenses, practice.activities,
                      practice.engagements, practice.companies RESTART IDENTITY CASCADE""")
    wipe()
    yield
    wipe()


def test_pipeline_weighting_and_follow_ups(clean):
    t = pm.today()
    pp.save_company(None, Form(name="A Co", kind="prospect", stage="proposal", est_value="10000",
                               next_step="Call", next_step_date=(t - dt.timedelta(days=1)).isoformat()))
    pp.save_company(None, Form(name="B Co", kind="prospect", stage="lead", est_value="20000"))
    o = pm.overview(t)
    assert o["pipeline"] == 30000 and o["pipeline_weighted"] == pytest.approx(10000 * 0.5 + 20000 * 0.05)
    fu = pm.follow_ups(t)
    assert [r["name"] for r in fu] == ["A Co"] and fu[0]["overdue"]


def test_activity_updates_company_and_won_makes_client(clean):
    cid = pp.save_company(None, Form(name="C Co", kind="prospect", stage="contacted"))
    pp.save_activity(None, Form(happened_on=pm.today().isoformat(), kind="meeting", summary="Good meeting",
                                next_step="Send proposal", next_step_date=pm.today().isoformat(), stage="won"), cid)
    c = db.one("SELECT kind, stage, next_step FROM practice.companies WHERE id = %(i)s", {"i": cid})
    assert (c["kind"], c["stage"], c["next_step"]) == ("client", "won", "Send proposal")
    assert pm.overview()["conversations_month"] == 1


def test_money_time_and_mrr(clean):
    t = pm.today()
    cid = pp.save_company(None, Form(name="D Co", kind="client"))
    pp.save_engagement(None, Form(company_id=str(cid), offer="retainer", name="Run & Grow", status="active",
                                  monthly_fee="2500", start_date=t.replace(day=1).isoformat()))
    pp.save_time(None, Form(work_date=t.isoformat(), hours="3", company_id=str(cid), billable="on"))
    pp.save_invoice(None, Form(company_id=str(cid), number="T-1", issued_date=t.isoformat(),
                               due_date=t.isoformat(), amount="2500"))
    o = pm.overview(t)
    assert o["mrr"] == 2500 and o["revenue_ytd"] == 2500 and o["unpaid"] == 2500 and o["hours_week"] == 3
    assert o["effective_rate"] == pytest.approx(2500 / 3)
    inv = db.one("SELECT id FROM practice.invoices WHERE number = 'T-1'")["id"]
    pp.mark_paid(inv)
    assert pm.overview(t)["cash_ytd"] == 2500 and pm.overview(t)["unpaid"] == 0


def test_forms_reject_bad_input(clean):
    with pytest.raises(forms.FormError) as e:
        pp.save_company(None, Form(name="", kind="prospect", est_value="-3"))
    assert "name" in e.value.errors and "est_value" in e.value.errors
    with pytest.raises(forms.FormError):
        pp.save_company(None, Form(name="X", kind="hacker"))  # not an allowed choice
    cid = pp.save_company(None, Form(name="E Co", kind="client"))
    pp.save_invoice(None, Form(company_id=str(cid), number="DUP", issued_date="2026-01-01", due_date="2026-01-15", amount="1"))
    with pytest.raises(forms.FormError):
        pp.save_invoice(None, Form(company_id=str(cid), number="DUP", issued_date="2026-01-01", due_date="2026-01-15", amount="1"))
    with pytest.raises(forms.FormError):
        pp.save_time(None, Form(work_date="2026-01-01", hours="30"))


def test_form_posts_need_the_token():
    import os
    from kit.passwords import hash_password
    os.environ["SECURE_COOKIES"] = "0"
    from kit.hub.auth import csrf_token
    class R:
        cookies = {"hub_session": "abc"}
    from kit.hub.auth import csrf_ok
    assert csrf_ok(R(), {"_csrf": csrf_token("abc")})
    assert not csrf_ok(R(), {"_csrf": "wrong"}) and not csrf_ok(R(), {})
