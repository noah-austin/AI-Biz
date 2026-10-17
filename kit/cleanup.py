"""The clean-up list: data problems to fix in the source systems.

Each check finds records that make reports wrong, says why it matters and
how to fix it, and links each record back to the system it lives in. We don't
patch these over in our reports; the client's team fixes them at the source,
and every number gets more accurate.
"""
from dataclasses import dataclass

from . import db


@dataclass
class Check:
    key: str
    title: str
    why: str
    fix: str
    system: str          # "crm" or "accounting"
    link: str            # key into config [links]
    sql: str             # returns id, label, detail, amount, branch_code


def _s(col="branch_code"):
    return f" AND ({col} = ANY(%(scope)s) OR %(scope)s IS NULL)"


CHECKS = [
    Check("placeholder_close", "Close date is a placeholder",
          "A won deal dated far in the future (like 2111) drops out of every bookings report, so real wins go uncounted.",
          "Set the close date to the day the deal was actually won.", "crm", "crm_deal",
          f"""SELECT id, name AS label, 'Close date ' || close_date AS detail, amount, branch_code FROM rpt.deals
              WHERE close_date > core.local_today() + interval '5 years' {_s()} ORDER BY amount DESC NULLS LAST"""),
    Check("duplicates", "Possible duplicate deals",
          "Two records for the same deal double-count the pipeline.",
          "Check with the owner; delete or merge the duplicate.", "crm", "crm_deal",
          f"""SELECT b.id, b.name AS label, 'Looks like ' || a.id || ' (same account, name and amount)' AS detail,
                     b.amount, b.branch_code
              FROM rpt.deals a JOIN rpt.deals b ON a.account_id = b.account_id AND lower(a.name) = lower(b.name)
                   AND a.amount = b.amount AND a.id < b.id AND abs(b.created_date - a.created_date) <= 7
              WHERE true {_s('b.branch_code')} ORDER BY b.amount DESC NULLS LAST"""),
    Check("stale_open", "Open deal with a close date more than 30 days ago",
          "These inflate the pipeline with deals that are probably already won or lost.",
          "Mark it won or lost, or move the close date to a realistic one.", "crm", "crm_deal",
          f"""SELECT id, name AS label, stage || ', close date ' || close_date || ' (' ||
                     (core.local_today() - close_date) || ' days ago)' AS detail, amount, branch_code
              FROM rpt.deals WHERE is_open AND close_date < core.local_today() - 30 {_s()}
              ORDER BY amount DESC NULLS LAST"""),
    Check("missing_margin", "Won deal with no margin entered (last 18 months)",
          "Margin reports can only use deals that have a margin, so gaps make margin % less reliable.",
          "Enter the estimated margin on the deal.", "crm", "crm_deal",
          f"""SELECT id, name AS label, 'Won ' || close_date AS detail, amount, branch_code FROM rpt.deals
              WHERE is_won AND margin_pct IS NULL AND close_date >= core.local_today() - interval '18 months'
                AND close_date <= core.local_today() {_s()} ORDER BY amount DESC NULLS LAST"""),
    Check("lost_no_reason", "Lost deal with no loss reason (last 12 months)",
          "Without reasons, we can't see why we lose or what to change.",
          "Pick the loss reason on the deal.", "crm", "crm_deal",
          f"""SELECT id, name AS label, 'Lost ' || close_date AS detail, amount, branch_code FROM rpt.deals
              WHERE is_lost AND loss_reason IS NULL AND close_date >= core.local_today() - interval '12 months'
                {_s()} ORDER BY amount DESC NULLS LAST"""),
    Check("won_not_billed", "Won more than 45 days ago, but no invoice found",
          "Either the work hasn't been billed (lost revenue) or the invoice doesn't reference the deal.",
          "Check with billing. If invoiced, add the deal number to the invoice's reference.", "crm", "crm_deal",
          f"""SELECT d.id, d.name AS label, d.deal_type || ', won ' || d.close_date AS detail, d.amount, d.branch_code
              FROM rpt.deals d
              WHERE d.is_won AND d.close_date BETWEEN core.local_today() - 365 AND core.local_today() - 45
                AND NOT EXISTS (SELECT 1 FROM rpt.invoices i WHERE i.deal_id = d.id) {_s('d.branch_code')}
              ORDER BY d.amount DESC NULLS LAST"""),
    Check("unlinked_customer", "Accounting customer not linked to a CRM account",
          "Their invoices can't be tied to a branch, segment or sales history.",
          "Add the CRM account ID to the customer record in accounting.", "accounting", "accounting_customer",
          """SELECT c.id, c.name AS label,
                    coalesce((SELECT count(*) FROM acct.invoices i WHERE i.customer_id = c.id), 0) || ' invoices' AS detail,
                    (SELECT sum(amount) FROM acct.invoices i WHERE i.customer_id = c.id) AS amount, NULL AS branch_code
             FROM acct.customers c
             WHERE (c.crm_account_id IS NULL OR NOT EXISTS (SELECT 1 FROM crm.accounts a WHERE a.id = c.crm_account_id))
               AND %(scope)s IS NULL
             ORDER BY amount DESC NULLS LAST"""),
    Check("unmapped_branch", "Deal with a branch code we don't recognise",
          "It won't roll up to a branch or region in any report.",
          "Fix the branch on the deal, or tell us the new branch so we can map it.", "crm", "crm_deal",
          """SELECT id, name AS label, 'Branch code ' || coalesce(branch_code, '(blank)') AS detail, amount, branch_code
             FROM rpt.deals WHERE region = 'Unmapped' AND %(scope)s IS NULL ORDER BY amount DESC NULLS LAST"""),
]


def run_checks(scope=None, limit=200) -> list[dict]:
    out = []
    for c in CHECKS:
        rows = db.query(c.sql, {"scope": scope})
        out.append({"check": c, "count": len(rows), "amount": sum(float(r["amount"] or 0) for r in rows),
                    "rows": rows[:limit]})
    return out


def counts(scope=None) -> dict:
    return {r["check"].key: r["count"] for r in run_checks(scope, limit=0)}
