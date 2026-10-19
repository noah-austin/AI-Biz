-- Standard tables for operations systems: HR and payroll, field service, inventory and purchasing.
-- Like 010_sources.sql, every connector for these systems maps into these tables. A client without
-- one of these systems simply has empty tables, and its pages stay switched off (see `apps` in config.toml).
CREATE SCHEMA IF NOT EXISTS hr;
CREATE SCHEMA IF NOT EXISTS fsm;
CREATE SCHEMA IF NOT EXISTS inv;
CREATE SCHEMA IF NOT EXISTS ap;

CREATE TABLE IF NOT EXISTS hr.employees (
    id text PRIMARY KEY, name text, email text, title text, department text, branch_code text,
    hire_date date, termination_date date, termination_type text, manager_id text, pay_type text,
    employment_type text, extra jsonb NOT NULL DEFAULT '{}', synced_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS hr.certifications (
    id text PRIMARY KEY, employee_id text, name text, issued_date date, expires_date date,
    synced_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS hr.timesheets (
    id text PRIMARY KEY, employee_id text, week_start date, regular_hours numeric, overtime_hours numeric,
    pto_hours numeric, approved boolean, synced_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS timesheets_week ON hr.timesheets (week_start);
CREATE TABLE IF NOT EXISTS hr.requisitions (
    id text PRIMARY KEY, title text, department text, branch_code text, opened_date date, filled_date date,
    status text, reason text, applicants integer, synced_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS fsm.work_orders (
    id text PRIMARY KEY, number text, account_id text, branch_code text, job_type text, priority text, status text,
    created_at timestamptz, scheduled_date date, arrived_at timestamptz, completed_at timestamptz,
    technician_id text, labor_hours numeric, billable boolean, billable_amount numeric, invoice_number text,
    is_callback boolean NOT NULL DEFAULT false, parent_id text,
    extra jsonb NOT NULL DEFAULT '{}', synced_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS work_orders_parent ON fsm.work_orders (parent_id);
CREATE INDEX IF NOT EXISTS work_orders_scheduled ON fsm.work_orders (scheduled_date);
CREATE TABLE IF NOT EXISTS fsm.work_order_parts (
    id text PRIMARY KEY, work_order_id text, sku text, qty numeric, location_id text, used_date date,
    synced_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS work_order_parts_used ON fsm.work_order_parts (used_date);

CREATE TABLE IF NOT EXISTS inv.items (
    id text PRIMARY KEY, description text, category text, standard_cost numeric, preferred_vendor_id text,
    critical boolean NOT NULL DEFAULT false, active boolean NOT NULL DEFAULT true,
    extra jsonb NOT NULL DEFAULT '{}', synced_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS inv.locations (
    id text PRIMARY KEY, name text, kind text, branch_code text, synced_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS inv.stock (
    id text PRIMARY KEY, location_id text, sku text, on_hand numeric, reorder_point numeric, reorder_qty numeric,
    last_issued_date date, last_counted_date date, synced_at timestamptz NOT NULL
);
-- Only ever added to: every count correction is kept.
CREATE TABLE IF NOT EXISTS inv.adjustments (
    id text PRIMARY KEY, adj_date date, location_id text, sku text, qty numeric, reason text,
    synced_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS ap.vendors (
    id text PRIMARY KEY, name text, category text, terms_days integer,
    extra jsonb NOT NULL DEFAULT '{}', synced_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS ap.purchase_orders (
    id text PRIMARY KEY, number text, vendor_id text, branch_code text, kind text, ordered_date date,
    expected_date date, received_date date, status text, amount numeric, billed_amount numeric, deal_id text,
    extra jsonb NOT NULL DEFAULT '{}', synced_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS ap.po_lines (
    id text PRIMARY KEY, po_id text, sku text, description text, qty numeric, unit_price numeric,
    synced_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS po_lines_po ON ap.po_lines (po_id);
