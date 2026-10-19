-- Standard tables for project and time tracking (a professional-services firm's PSA: projects, budgets, time).
CREATE SCHEMA IF NOT EXISTS psa;

CREATE TABLE IF NOT EXISTS psa.projects (
    id text PRIMARY KEY, number text, name text, account_id text, deal_id text, branch_code text, pm_id text,
    billing_type text, contract_value numeric, budget_hours numeric, start_date date, end_date date, status text,
    percent_complete numeric, extra jsonb NOT NULL DEFAULT '{}', synced_at timestamptz NOT NULL
);
-- Time by person, project and week. project_id NULL = internal (non-billable) time.
CREATE TABLE IF NOT EXISTS psa.time_entries (
    id text PRIMARY KEY, employee_id text, project_id text, week_ending date, hours numeric, billable boolean,
    bill_rate numeric, cost_rate numeric, invoice_number text, synced_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS time_entries_week ON psa.time_entries (week_ending);
CREATE INDEX IF NOT EXISTS time_entries_project ON psa.time_entries (project_id);
