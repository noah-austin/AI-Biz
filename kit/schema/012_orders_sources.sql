-- Standard tables for sales orders and shipping (a distributor's ERP: orders, order lines, what shipped when).
CREATE SCHEMA IF NOT EXISTS ord;

CREATE TABLE IF NOT EXISTS ord.orders (
    id text PRIMARY KEY, number text, account_id text, branch_code text, rep_id text, channel text,
    order_date date, requested_date date, status text, first_ship_date date, last_ship_date date, invoice_number text,
    extra jsonb NOT NULL DEFAULT '{}', synced_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS orders_date ON ord.orders (order_date);
CREATE TABLE IF NOT EXISTS ord.order_lines (
    id text PRIMARY KEY, order_id text, sku text, qty_ordered numeric, qty_first_shipment numeric, qty_shipped numeric,
    unit_price numeric, unit_cost numeric, synced_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS order_lines_order ON ord.order_lines (order_id);
