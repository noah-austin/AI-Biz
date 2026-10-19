-- Job cost and the work-in-progress (WIP) schedule. Business rules live here once; the rulebook says the same in words.
DROP VIEW IF EXISTS rpt.wip CASCADE;

-- One row per job, as of the end of last month (the way contractors close the books each month).
-- Contract = original contract + approved change orders. Percent complete = cost to date ÷ estimated cost at completion
-- (cost-to-cost). Earned = percent complete × contract. Over/(under) billed = billed to date − earned.
-- Original margin is from the bid; projected margin is from today's estimate. Fade = original − projected.
CREATE VIEW rpt.wip AS
WITH as_of AS (SELECT date_trunc('month', core.local_today())::date AS m),
co AS (SELECT job_id, sum(amount) FILTER (WHERE status = 'Approved') AS approved,
              sum(amount) FILTER (WHERE status = 'Pending') AS pending,
              count(*) FILTER (WHERE status = 'Pending') AS pending_n,
              min(submitted_date) FILTER (WHERE status = 'Pending') AS oldest_pending
       FROM jc.change_orders GROUP BY 1),
c AS (SELECT job_id, sum(amount) AS cost FROM jc.costs, as_of WHERE period < as_of.m GROUP BY 1),
b AS (SELECT job_id, sum(gross_billed) AS billed, sum(retainage_held) - sum(retainage_released) AS retainage
      FROM jc.pay_apps, as_of WHERE period < as_of.m GROUP BY 1)
SELECT j.id, j.number, j.name, j.account_id, a.name AS account_name, a.segment, j.deal_id, j.branch_code,
       coalesce(br.name, j.branch_code) AS branch, j.pm_id, pm.name AS pm_name, j.status, j.start_date, j.end_date,
       j.contract_value AS original_contract, coalesce(co.approved, 0) AS approved_changes,
       j.contract_value + coalesce(co.approved, 0) AS contract,
       coalesce(co.pending, 0) AS pending_changes, coalesce(co.pending_n, 0) AS pending_n, co.oldest_pending,
       j.budget_cost, j.estimate_at_completion AS est_cost, coalesce(c.cost, 0) AS cost_to_date,
       least(1, coalesce(c.cost, 0) / nullif(j.estimate_at_completion, 0)) AS pct_complete,
       least(1, coalesce(c.cost, 0) / nullif(j.estimate_at_completion, 0)) * (j.contract_value + coalesce(co.approved, 0)) AS earned,
       coalesce(b.billed, 0) AS billed, coalesce(b.retainage, 0) AS retainage,
       coalesce(b.billed, 0) - least(1, coalesce(c.cost, 0) / nullif(j.estimate_at_completion, 0)) * (j.contract_value + coalesce(co.approved, 0)) AS over_under,
       (j.contract_value - j.budget_cost) / nullif(j.contract_value, 0) AS original_margin,
       (j.contract_value + coalesce(co.approved, 0) - j.estimate_at_completion) / nullif(j.contract_value + coalesce(co.approved, 0), 0) AS projected_margin
FROM jc.jobs j
LEFT JOIN crm.accounts a ON a.id = j.account_id
LEFT JOIN hr.employees pm ON pm.id = j.pm_id
LEFT JOIN core.branches br ON br.code = j.branch_code
LEFT JOIN co ON co.job_id = j.id
LEFT JOIN c ON c.job_id = j.id
LEFT JOIN b ON b.job_id = j.id;
