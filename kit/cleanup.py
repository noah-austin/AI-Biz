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
    system: str          # which system it's fixed in: a key of SYSTEMS
    link: str            # key into config [links]
    sql: str             # returns id, label, detail, amount, branch_code, branch, owner_name
    app: str = "analytics"   # only run for installs with this app (and so this system) switched on


SYSTEMS = {"crm": "CRM", "accounting": "Accounting", "orders": "Orders (ERP)", "projects": "Projects and time", "jobcost": "Job cost", "fieldservice": "Field service", "inventory": "Inventory",
           "purchasing": "Purchasing", "hr": "HR and payroll"}


def _s(col="branch_code"):
    return f" AND ({col} = ANY(%(scope)s) OR %(scope)s IS NULL)"


CHECKS = [
    Check("placeholder_close", "Close date is a placeholder",
          "A won deal dated far in the future (like 2111) drops out of every bookings report, so real wins go uncounted.",
          "Set the close date to the day the deal was actually won.", "crm", "crm_deal",
          f"""SELECT id, name AS label, 'Close date ' || to_char(close_date, 'Mon FMDD, YYYY') AS detail, amount, branch_code, branch, owner_name FROM rpt.deals
              WHERE close_date > core.local_today() + interval '5 years' {_s()} ORDER BY amount DESC NULLS LAST"""),
    Check("duplicates", "Possible duplicate deals",
          "Two records for the same deal double-count the pipeline.",
          "Check with the owner; delete or merge the duplicate.", "crm", "crm_deal",
          f"""SELECT b.id, b.name AS label, 'Looks like ' || a.id || ' (same account, name and amount)' AS detail,
                     b.amount, b.branch_code, b.branch, b.owner_name
              FROM rpt.deals a JOIN rpt.deals b ON a.account_id = b.account_id AND lower(a.name) = lower(b.name)
                   AND a.amount = b.amount AND a.id < b.id AND abs(b.created_date - a.created_date) <= 7
              WHERE true {_s('b.branch_code')} ORDER BY b.amount DESC NULLS LAST"""),
    Check("stale_open", "Open deal with a close date more than 30 days ago",
          "These inflate the pipeline with deals that are probably already won or lost.",
          "Mark it won or lost, or move the close date to a realistic one.", "crm", "crm_deal",
          f"""SELECT id, name AS label, stage || ', close date ' || to_char(close_date, 'Mon FMDD, YYYY') || ' (' ||
                     (core.local_today() - close_date) || ' days ago)' AS detail, amount, branch_code, branch, owner_name
              FROM rpt.deals WHERE is_open AND close_date < core.local_today() - 30 {_s()}
              ORDER BY amount DESC NULLS LAST"""),
    Check("missing_margin", "Won deal with no margin entered (last 18 months)",
          "Margin reports can only use deals that have a margin, so gaps make margin % less reliable.",
          "Enter the estimated margin on the deal.", "crm", "crm_deal",
          f"""SELECT id, name AS label, 'Won ' || to_char(close_date, 'Mon FMDD, YYYY') AS detail, amount, branch_code, branch, owner_name FROM rpt.deals
              WHERE is_won AND margin_pct IS NULL AND close_date >= core.local_today() - interval '18 months'
                AND close_date <= core.local_today() {_s()} ORDER BY amount DESC NULLS LAST"""),
    Check("lost_no_reason", "Lost deal with no loss reason (last 12 months)",
          "Without reasons, we can't see why we lose or what to change.",
          "Pick the loss reason on the deal.", "crm", "crm_deal",
          f"""SELECT id, name AS label, 'Lost ' || to_char(close_date, 'Mon FMDD, YYYY') AS detail, amount, branch_code, branch, owner_name FROM rpt.deals
              WHERE is_lost AND loss_reason IS NULL AND close_date >= core.local_today() - interval '12 months'
                {_s()} ORDER BY amount DESC NULLS LAST"""),
    Check("won_not_billed", "Won more than 45 days ago, but no invoice found",
          "Either the work hasn't been billed (lost revenue) or the invoice doesn't reference the deal.",
          "Check with billing. If invoiced, add the deal number to the invoice's reference.", "crm", "crm_deal",
          f"""SELECT d.id, d.name AS label, d.deal_type || ', won ' || to_char(d.close_date, 'Mon FMDD, YYYY') AS detail, d.amount, d.branch_code,
                     d.branch, d.owner_name
              FROM rpt.deals d
              WHERE d.is_won AND d.close_date BETWEEN core.local_today() - 365 AND core.local_today() - 45
                AND NOT EXISTS (SELECT 1 FROM rpt.invoices i WHERE i.deal_id = d.id) {_s('d.branch_code')}
              ORDER BY d.amount DESC NULLS LAST"""),
    Check("unlinked_customer", "Accounting customer not linked to a CRM account",
          "Their invoices can't be tied to a branch, segment or sales history.",
          "Add the CRM account ID to the customer record in accounting.", "accounting", "accounting_customer",
          """SELECT c.id, c.name AS label,
                    coalesce((SELECT count(*) FROM acct.invoices i WHERE i.customer_id = c.id), 0) || ' invoices' AS detail,
                    (SELECT sum(amount) FROM acct.invoices i WHERE i.customer_id = c.id) AS amount, NULL AS branch_code,
                    NULL AS branch, 'Accounting team' AS owner_name
             FROM acct.customers c
             WHERE (c.crm_account_id IS NULL OR NOT EXISTS (SELECT 1 FROM crm.accounts a WHERE a.id = c.crm_account_id))
               AND %(scope)s IS NULL
             ORDER BY amount DESC NULLS LAST"""),
    Check("unmapped_branch", "Deal with a branch code we don't recognise",
          "It won't roll up to a branch or region in any report.",
          "Fix the branch on the deal, or tell us the new branch so we can map it.", "crm", "crm_deal",
          """SELECT id, name AS label, 'Branch code ' || coalesce(branch_code, '(blank)') AS detail, amount, branch_code,
                    branch, owner_name
             FROM rpt.deals WHERE region = 'Unmapped' AND %(scope)s IS NULL ORDER BY amount DESC NULLS LAST"""),
    Check("loss_job", "Active job projected to lose money",
          "Its estimated cost at completion is more than its contract: every month makes it worse unless something changes.",
          "Review the estimate with the project manager; chase change orders and back-charges.", "jobcost", "jc_job",
          f"""SELECT id, 'Job ' || number || ' · ' || name AS label,
                     'Projected margin ' || round(projected_margin * 100, 1) || '%%, bid at ' || round(original_margin * 100, 1) || '%%' AS detail,
                     est_cost - contract AS amount, branch_code, branch, coalesce(pm_name, 'Operations') AS owner_name
              FROM rpt.wip WHERE status = 'Active' AND projected_margin < 0 {_s()} ORDER BY projected_margin""", "job_cost"),
    Check("stale_change_order", "Change order waiting on the owner for 60+ days",
          "The work is often already done; the longer it waits, the harder it is to get paid.",
          "Escalate with the owner, or price it into the next pay application.", "jobcost", "jc_job",
          f"""SELECT id, 'Job ' || number || ' · ' || name AS label,
                     pending_n || ' waiting, oldest from ' || to_char(oldest_pending, 'Mon FMDD, YYYY') AS detail,
                     pending_changes AS amount, branch_code, branch, coalesce(pm_name, 'Operations') AS owner_name
              FROM rpt.wip WHERE status = 'Active' AND oldest_pending < core.local_today() - 60 {_s()}
              ORDER BY oldest_pending""", "job_cost"),
    Check("under_billed", "Job under-billed by more than $100K",
          "Work done but not billed: the company is paying for the owner's job.",
          "Catch up on the next pay application.", "jobcost", "jc_job",
          f"""SELECT id, 'Job ' || number || ' · ' || name AS label, round(pct_complete * 100) || '%% complete, billed ' ||
                     round(billed / nullif(contract, 0) * 100) || '%% of contract' AS detail, -over_under AS amount,
                     branch_code, branch, coalesce(pm_name, 'Billing') AS owner_name
              FROM rpt.wip WHERE status = 'Active' AND over_under < -100000 {_s()} ORDER BY over_under""", "job_cost"),
    Check("time_not_billed", "Hourly project with time not billed for 60+ days",
          "Work done but not invoiced is cash the firm is lending its client, and it gets harder to collect the older it is.",
          "Bill the time, or write down what won't be billed, with the project manager's say-so.", "projects", "psa_project",
          f"""SELECT id, 'Project ' || number || ' · ' || name AS label,
                     'Unbilled since ' || to_char(oldest_unbilled, 'Mon FMDD, YYYY') AS detail, unbilled_value AS amount,
                     branch_code, branch, coalesce(pm_name, 'Billing') AS owner_name
              FROM rpt.projects WHERE billing_type = 'Time & materials' AND unbilled_value > 0
                AND oldest_unbilled < core.local_today() - 60 {_s()} ORDER BY unbilled_value DESC""", "projects"),
    Check("over_budget", "Fixed-fee project past its budget hours",
          "Every hour from here is unpaid. If the scope grew, it needs a change order.",
          "Raise a change order with the client, or agree a recovery plan with the project manager.", "projects", "psa_project",
          f"""SELECT id, 'Project ' || number || ' · ' || name AS label,
                     round(budget_used * 100) || '%% of budget hours used, ' || round(percent_complete) || '%% complete' AS detail,
                     (hours - budget_hours) * (standard_value / nullif(hours, 0)) AS amount, branch_code, branch,
                     coalesce(pm_name, 'Projects') AS owner_name
              FROM rpt.projects WHERE status = 'Active' AND billing_type = 'Fixed fee' AND budget_used > 1 {_s()}
              ORDER BY budget_used DESC""", "projects"),
    Check("order_not_invoiced", "Order shipped but not invoiced after 5 days",
          "Goods are gone but the bill never went out.",
          "Invoice the order, or record why it isn't billable.", "orders", "ord_order",
          f"""SELECT id, 'Order ' || number || ' · ' || coalesce(account_name, '') AS label,
                     'Shipped ' || to_char(last_ship_date, 'Mon FMDD, YYYY') AS detail, sales AS amount, branch_code, branch,
                     'Billing team' AS owner_name
              FROM rpt.orders WHERE status = 'Shipped' AND invoice_number IS NULL AND last_ship_date <= core.local_today() - 5 {_s()}
              ORDER BY sales DESC NULLS LAST""", "orders"),
    Check("below_cost", "Order line priced below cost (last 90 days)",
          "Every unit sold loses money; usually a typo in the price or an override nobody approved.",
          "Check the price with the rep; fix the price list or the customer's special pricing.", "orders", "ord_order",
          f"""SELECT order_id AS id, 'Order ' || order_number || ' · ' || description AS label,
                     to_char(unit_price, 'FM$999,990.00') || ' each, cost ' || to_char(unit_cost, 'FM$999,990.00') AS detail,
                     cost - sales AS amount, branch_code, branch, coalesce(rep_name, 'Sales') AS owner_name
              FROM rpt.order_lines WHERE status <> 'Canceled' AND unit_price < unit_cost
                AND order_date >= core.local_today() - 90 {_s()} ORDER BY cost - sales DESC""", "orders"),
    Check("job_not_invoiced", "Completed job not invoiced after 14 days",
          "Work that's done but never billed is revenue that quietly disappears.",
          "Raise the invoice, or note on the job why it isn't billable.", "fieldservice", "fsm_job",
          f"""SELECT id, 'Job ' || number || ' · ' || coalesce(account_name, 'no customer') AS label,
                     job_type || ', completed ' || to_char(completed_date, 'Mon FMDD, YYYY') AS detail, billable_amount AS amount,
                     branch_code, branch, 'Service coordinator' AS owner_name
              FROM rpt.jobs WHERE status = 'Completed' AND billable AND invoice_number IS NULL
                AND completed_date <= core.local_today() - 14 {_s()} ORDER BY billable_amount DESC NULLS LAST""", "field_service"),
    Check("job_left_tech", "Job booked to someone who has left",
          "Nobody will turn up: the customer waits and the call is missed.",
          "Reassign the job to a current technician.", "fieldservice", "fsm_job",
          f"""SELECT id, 'Job ' || number || ' · ' || coalesce(account_name, '') AS label,
                     'Booked to ' || technician_name || ' for ' || to_char(scheduled_date, 'Mon FMDD') || ', who has left' AS detail,
                     billable_amount AS amount, branch_code, branch, 'Service coordinator' AS owner_name
              FROM rpt.jobs WHERE is_open AND technician_id IS NOT NULL AND NOT technician_active {_s()}
              ORDER BY scheduled_date""", "field_service"),
    Check("expired_license_booked", "Still working on an expired license",
          "Working without a current license is a compliance and insurance risk.",
          "Renew the license, or take them off the work that needs it until it's renewed.", "hr", "hr_employee",
          f"""SELECT c.employee_id AS id, c.employee_name AS label,
                     c.certification || ' expired ' || to_char(c.expires_date, 'Mon FMDD, YYYY') AS detail,
                     NULL::numeric AS amount, c.branch_code, c.branch, coalesce(e.manager_name, 'HR') AS owner_name
              FROM rpt.certifications c JOIN rpt.employees e ON e.id = c.employee_id
              WHERE c.is_active AND c.status = 'Expired' AND c.is_license {_s('c.branch_code')}""", "people"),
    Check("missing_timesheet", "No timesheet for last week",
          "Payroll can't run correctly, and overtime and utilization are understated.",
          "Submit and approve last week's timesheet.", "hr", "hr_employee",
          f"""SELECT e.id, e.name AS label, e.title || ', week of ' ||
                     to_char(date_trunc('week', core.local_today())::date - 7, 'Mon FMDD') AS detail,
                     NULL::numeric AS amount, e.branch_code, e.branch, coalesce(e.manager_name, 'HR') AS owner_name
              FROM rpt.employees e
              WHERE e.is_active AND e.pay_type = 'Hourly' AND e.hire_date <= date_trunc('week', core.local_today())::date - 7
                AND NOT EXISTS (SELECT 1 FROM hr.timesheets t WHERE t.employee_id = e.id
                                AND t.week_start = date_trunc('week', core.local_today())::date - 7) {_s('e.branch_code')}""", "people"),
    Check("no_manager", "Employee with no manager",
          "Nobody approves their time off or timesheets, and they drop out of team reports.",
          "Set their manager in HR.", "hr", "hr_employee",
          f"""SELECT id, name AS label, title || ', hired ' || to_char(hire_date, 'Mon FMDD, YYYY') AS detail, NULL::numeric AS amount,
                     branch_code, branch, 'HR' AS owner_name
              FROM rpt.employees WHERE is_active AND manager_id IS NULL AND title <> 'President' {_s()}""", "people"),
    Check("negative_stock", "Negative stock on hand",
          "Parts were used before they were received, so stock and reorder points are wrong.",
          "Count the shelf and post the missing receipt or a count correction.", "inventory", "inv_item",
          f"""SELECT sku AS id, description AS label, location || ': ' || on_hand || ' on hand' AS detail, NULL::numeric AS amount,
                     branch_code, branch, 'Parts clerk' AS owner_name
              FROM rpt.stock WHERE on_hand < 0 {_s()}""", "inventory"),
    Check("item_no_cost", "Part with no standard cost",
          "It's left out of inventory value and job costs.",
          "Enter the standard cost on the item.", "inventory", "inv_item",
          """SELECT i.id, i.description AS label, coalesce((SELECT sum(on_hand) FROM inv.stock s WHERE s.sku = i.id), 0) || ' on hand' AS detail,
                    NULL::numeric AS amount, NULL AS branch_code, NULL AS branch, 'Purchasing' AS owner_name
             FROM inv.items i WHERE i.standard_cost IS NULL AND %(scope)s IS NULL""", "inventory"),
    Check("po_not_billed", "Received over 30 days ago, no vendor bill",
          "The cost is real but missing from the books, so margins look better than they are.",
          "Ask the vendor for the bill, or match it if it's already in.", "purchasing", "ap_po",
          f"""SELECT id, 'PO ' || number || ' · ' || vendor AS label, kind || ', received ' || to_char(received_date, 'Mon FMDD, YYYY') AS detail,
                     amount, branch_code, branch, 'AP team' AS owner_name
              FROM rpt.purchase_orders WHERE status = 'Received' AND received_date <= core.local_today() - 30 {_s()}
              ORDER BY amount DESC""", "purchasing"),
    Check("duplicate_vendor", "Possible duplicate vendor",
          "Spend is split across two records, and the same bill can be paid twice.",
          "Merge the vendors and make the older record inactive.", "purchasing", "ap_vendor",
          """SELECT b.id, b.name AS label, 'Looks like ' || a.name AS detail,
                    (SELECT sum(amount) FROM ap.purchase_orders p WHERE p.vendor_id = b.id) AS amount,
                    NULL AS branch_code, NULL AS branch, 'AP team' AS owner_name
             FROM ap.vendors a JOIN ap.vendors b ON a.id < b.id
                  AND regexp_replace(lower(a.name), '\\m(and|inc|llc|co)\\M|[^a-z]', '', 'g')
                    = regexp_replace(lower(b.name), '\\m(and|inc|llc|co)\\M|[^a-z]', '', 'g')
             WHERE %(scope)s IS NULL""", "purchasing"),
]


def run_checks(scope=None, limit=200) -> list[dict]:
    from .config import get_settings
    apps = get_settings().apps
    skip = set(get_settings().client.get("checks", {}).get("skip", []))   # checks that don't fit how this company works
    out = []
    for c in CHECKS:
        if c.app not in apps or c.key in skip:
            continue
        rows = db.query(c.sql, {"scope": scope})
        out.append({"check": c, "count": len(rows), "amount": sum(float(r["amount"] or 0) for r in rows),
                    "rows": rows[:limit], "all_rows": rows})
    return out


def counts(scope=None) -> dict:
    return {r["check"].key: r["count"] for r in run_checks(scope, limit=0)}


def by_branch(results) -> list[dict]:
    """How many records each branch has to fix, across all checks. Items with no branch are grouped by the system they're in."""
    tally = {}
    for r in results:
        for row in r["all_rows"]:
            name = row.get("branch") or SYSTEMS.get(r["check"].system, "Other")
            t = tally.setdefault(name, {"branch": name, "count": 0, "checks": {}})
            t["count"] += 1
            t["checks"][r["check"].key] = t["checks"].get(r["check"].key, 0) + 1
    return sorted(tally.values(), key=lambda t: -t["count"])
