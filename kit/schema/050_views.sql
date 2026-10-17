-- The analytical views. Every page, report and AI question starts here.
-- Business rules that apply everywhere live here once (see the client's rulebook).
DROP VIEW IF EXISTS rpt.deal_history, rpt.invoices, rpt.deals, rpt.branches CASCADE;

CREATE VIEW rpt.branches AS
SELECT code, name, region, active FROM core.branches;

-- One row per deal. Rule: deals flagged "exclude from reporting" never appear.
CREATE VIEW rpt.deals AS
SELECT o.id, o.name, o.account_id, a.name AS account_name, a.segment,
       o.owner_id, u.name AS owner_name,
       o.branch_code, coalesce(b.name, o.branch_code) AS branch, coalesce(b.region, 'Unmapped') AS region,
       o.deal_type, o.stage, o.is_closed, o.is_won,
       (o.is_closed AND NOT o.is_won) AS is_lost, (NOT o.is_closed) AS is_open,
       o.probability, o.amount,
       o.amount * o.probability / 100.0 AS weighted_amount,
       o.margin_pct,
       CASE WHEN o.margin_pct IS NOT NULL THEN o.amount * o.margin_pct / 100.0 END AS margin_amount,
       o.close_date,
       (o.created_at AT TIME ZONE core.client_tz())::date AS created_date,
       o.created_at, o.modified_at, o.loss_reason, o.lead_source
FROM crm.opportunities o
LEFT JOIN crm.accounts a ON a.id = o.account_id
LEFT JOIN crm.users u ON u.id = o.owner_id
LEFT JOIN core.branches b ON b.code = o.branch_code
WHERE NOT o.exclude_from_reporting;

-- One row per invoice, linked to the CRM through the customer and the deal reference.
CREATE VIEW rpt.invoices AS
SELECT i.id, i.number, i.customer_id, c.name AS customer_name,
       c.crm_account_id AS account_id, a.segment,
       i.reference AS deal_id,
       coalesce(o.branch_code, a.branch_code) AS branch_code,
       coalesce(b.name, o.branch_code, a.branch_code, 'Unassigned') AS branch,
       coalesce(b.region, 'Unmapped') AS region,
       i.invoice_date, i.due_date, i.amount, i.amount_paid, i.paid_date,
       i.amount - coalesce(i.amount_paid, 0) AS balance,
       (i.amount - coalesce(i.amount_paid, 0)) > 0.005 AS is_open,
       CASE WHEN (i.amount - coalesce(i.amount_paid, 0)) > 0.005
            THEN greatest(0, core.local_today() - i.due_date) END AS days_past_due,
       CASE WHEN (i.amount - coalesce(i.amount_paid, 0)) <= 0.005 THEN 'Paid'
            WHEN core.local_today() <= i.due_date THEN 'Current'
            WHEN core.local_today() - i.due_date <= 30 THEN '1–30 days'
            WHEN core.local_today() - i.due_date <= 60 THEN '31–60 days'
            WHEN core.local_today() - i.due_date <= 90 THEN '61–90 days'
            ELSE 'Over 90 days' END AS aging_bucket,
       i.memo
FROM acct.invoices i
LEFT JOIN acct.customers c ON c.id = i.customer_id
LEFT JOIN crm.accounts a ON a.id = c.crm_account_id
LEFT JOIN crm.opportunities o ON o.id = i.reference
LEFT JOIN core.branches b ON b.code = coalesce(o.branch_code, a.branch_code);

CREATE VIEW rpt.deal_history AS
SELECT h.id, h.opportunity_id AS deal_id, d.name AS deal_name, d.account_name, d.branch_code, d.branch,
       d.deal_type, d.owner_name, h.field, h.old_value, h.new_value, h.changed_at,
       (h.changed_at AT TIME ZONE core.client_tz())::date AS changed_date
FROM crm.opportunity_history h
JOIN rpt.deals d ON d.id = h.opportunity_id;
