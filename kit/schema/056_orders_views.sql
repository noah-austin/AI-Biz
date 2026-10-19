-- Orders and shipping. Business rules live here once; the client's rulebook says the same in words.
DROP VIEW IF EXISTS rpt.orders, rpt.order_lines CASCADE;

-- One row per order line. Sales and cost count what shipped, at the order's price and cost.
-- Filled first time = the first shipment carried the whole quantity ordered.
-- Backorder = what's still owed on an order that has already shipped once (new orders not yet shipped aren't backorders).
CREATE VIEW rpt.order_lines AS
SELECT l.id, l.order_id, o.number AS order_number, o.account_id, a.name AS account_name, a.segment,
       o.branch_code, coalesce(b.name, o.branch_code) AS branch, coalesce(b.region, 'Unmapped') AS region,
       o.rep_id, u.name AS rep_name, o.channel, o.order_date, o.first_ship_date, o.last_ship_date, o.status,
       l.sku, coalesce(i.description, l.sku) AS description, coalesce(i.category, 'Other') AS product_line,
       l.qty_ordered, l.qty_first_shipment, l.qty_shipped, l.unit_price, l.unit_cost,
       l.qty_shipped * l.unit_price AS sales, l.qty_shipped * l.unit_cost AS cost,
       CASE WHEN o.first_ship_date IS NOT NULL AND o.status <> 'Canceled' THEN (l.qty_ordered - l.qty_shipped) * l.unit_price ELSE 0 END
           AS backorder_value,
       (l.qty_first_shipment >= l.qty_ordered) AS filled_first_time
FROM ord.order_lines l
JOIN ord.orders o ON o.id = l.order_id
LEFT JOIN crm.accounts a ON a.id = o.account_id
LEFT JOIN crm.users u ON u.id = o.rep_id
LEFT JOIN inv.items i ON i.id = l.sku
LEFT JOIN core.branches b ON b.code = o.branch_code;

-- One row per order. On time = first shipment on or before the date the customer asked for.
CREATE VIEW rpt.orders AS
SELECT o.id, o.number, o.account_id, a.name AS account_name, a.segment, o.branch_code,
       coalesce(b.name, o.branch_code) AS branch, o.rep_id, u.name AS rep_name, o.channel, o.order_date, o.requested_date,
       o.status, o.first_ship_date, o.last_ship_date, o.invoice_number,
       CASE WHEN o.first_ship_date IS NOT NULL AND o.requested_date IS NOT NULL THEN o.first_ship_date <= o.requested_date END AS on_time,
       (SELECT sum(l.qty_shipped * l.unit_price) FROM ord.order_lines l WHERE l.order_id = o.id) AS sales,
       CASE WHEN o.first_ship_date IS NOT NULL AND o.status <> 'Canceled'
            THEN (SELECT sum((l.qty_ordered - l.qty_shipped) * l.unit_price) FROM ord.order_lines l WHERE l.order_id = o.id) ELSE 0 END
           AS backorder_value
FROM ord.orders o
LEFT JOIN crm.accounts a ON a.id = o.account_id
LEFT JOIN crm.users u ON u.id = o.rep_id
LEFT JOIN core.branches b ON b.code = o.branch_code;
