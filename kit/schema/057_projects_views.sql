-- Projects and time. Business rules live here once; the client's rulebook says the same in words.
DROP VIEW IF EXISTS rpt.time_entries, rpt.projects CASCADE;

-- Time by person, project and week, at standard rates. Standard value = hours × the person's standard bill rate.
CREATE VIEW rpt.time_entries AS
SELECT t.id, t.employee_id, e.name AS employee_name, e.title, e.department, e.branch_code, e.branch,
       t.project_id, p.number AS project_number, p.billing_type, t.week_ending, t.hours, t.billable,
       t.hours * t.bill_rate AS standard_value, t.hours * t.cost_rate AS cost, t.invoice_number
FROM psa.time_entries t
JOIN rpt.employees e ON e.id = t.employee_id
LEFT JOIN psa.projects p ON p.id = t.project_id;

-- One row per project, with hours, cost and billing to date. Billed = accounting invoices whose Reference is the
-- project's CRM deal. Budget used = hours to date ÷ budget hours.
CREATE VIEW rpt.projects AS
SELECT p.id, p.number, p.name, p.account_id, a.name AS account_name, a.segment, p.deal_id, p.branch_code,
       coalesce(b.name, p.branch_code) AS branch, p.pm_id, e.name AS pm_name, p.billing_type, p.contract_value,
       p.budget_hours, p.start_date, p.end_date, p.status, p.percent_complete,
       coalesce(t.hours, 0) AS hours, coalesce(t.standard_value, 0) AS standard_value, coalesce(t.cost, 0) AS cost,
       coalesce(t.unbilled_value, 0) AS unbilled_value, t.oldest_unbilled,
       coalesce(i.billed, 0) AS billed,
       coalesce(t.hours, 0) / nullif(p.budget_hours, 0) AS budget_used
FROM psa.projects p
LEFT JOIN crm.accounts a ON a.id = p.account_id
LEFT JOIN hr.employees e ON e.id = p.pm_id
LEFT JOIN core.branches b ON b.code = p.branch_code
LEFT JOIN (SELECT project_id, sum(hours) AS hours, sum(hours * bill_rate) AS standard_value, sum(hours * cost_rate) AS cost,
                  sum(hours * bill_rate) FILTER (WHERE invoice_number IS NULL) AS unbilled_value,
                  min(week_ending) FILTER (WHERE invoice_number IS NULL) AS oldest_unbilled
           FROM psa.time_entries WHERE project_id IS NOT NULL GROUP BY 1) t ON t.project_id = p.id
LEFT JOIN (SELECT reference, sum(amount) AS billed FROM acct.invoices GROUP BY 1) i ON i.reference = p.deal_id;
