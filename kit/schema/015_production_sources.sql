-- Standard tables for production (a manufacturer's work centers, production orders and downtime).
CREATE SCHEMA IF NOT EXISTS mfg;

CREATE TABLE IF NOT EXISTS mfg.work_centers (
    id text PRIMARY KEY, name text, branch_code text, hours_per_day numeric, synced_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS mfg.production_orders (
    id text PRIMARY KEY, number text, sku text, work_center_id text, branch_code text, qty_planned numeric,
    qty_completed numeric, qty_scrapped numeric, due_date date, start_date date, completed_date date, status text,
    standard_hours numeric, actual_hours numeric, extra jsonb NOT NULL DEFAULT '{}', synced_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS production_orders_done ON mfg.production_orders (completed_date);
CREATE TABLE IF NOT EXISTS mfg.downtime (
    id text PRIMARY KEY, work_center_id text, event_date date, minutes numeric, reason text, synced_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS downtime_date ON mfg.downtime (event_date);
