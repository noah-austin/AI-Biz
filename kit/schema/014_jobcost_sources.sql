-- Standard tables for job costing (a contractor's jobs, change orders, monthly costs and pay applications).
CREATE SCHEMA IF NOT EXISTS jc;

CREATE TABLE IF NOT EXISTS jc.jobs (
    id text PRIMARY KEY, number text, name text, account_id text, deal_id text, branch_code text, pm_id text, super_id text,
    contract_value numeric, budget_cost numeric, estimate_at_completion numeric, start_date date, end_date date, status text,
    retainage_pct numeric, extra jsonb NOT NULL DEFAULT '{}', synced_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS jc.change_orders (
    id text PRIMARY KEY, job_id text, number text, description text, amount numeric, cost numeric, status text,
    submitted_date date, approved_date date, synced_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS jc.costs (
    id text PRIMARY KEY, job_id text, period date, category text, amount numeric, synced_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS jc_costs_job ON jc.costs (job_id, period);
CREATE TABLE IF NOT EXISTS jc.pay_apps (
    id text PRIMARY KEY, job_id text, period date, gross_billed numeric, retainage_held numeric, retainage_released numeric,
    bill_date date, synced_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS jc_pay_apps_job ON jc.pay_apps (job_id, period);
