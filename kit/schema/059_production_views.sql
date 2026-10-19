-- Production. Business rules live here once; the client's rulebook says the same in words.
DROP VIEW IF EXISTS rpt.production_orders, rpt.downtime CASCADE;

-- One row per production order. On time = completed on or before its due date.
-- Scrap rate = scrapped ÷ (completed + scrapped). Labor efficiency = standard hours ÷ actual hours.
CREATE VIEW rpt.production_orders AS
SELECT o.id, o.number, o.sku, coalesce(i.description, o.sku) AS description, coalesce(i.category, 'Other') AS product_family,
       o.work_center_id, w.name AS work_center, o.branch_code, coalesce(b.name, o.branch_code) AS plant,
       o.qty_planned, o.qty_completed, o.qty_scrapped, o.due_date, o.start_date, o.completed_date, o.status,
       o.standard_hours, o.actual_hours,
       CASE WHEN o.completed_date IS NOT NULL THEN o.completed_date <= o.due_date END AS on_time,
       (o.status <> 'Completed' AND o.due_date < core.local_today()) AS is_late
FROM mfg.production_orders o
LEFT JOIN mfg.work_centers w ON w.id = o.work_center_id
LEFT JOIN inv.items i ON i.id = o.sku
LEFT JOIN core.branches b ON b.code = o.branch_code;

CREATE VIEW rpt.downtime AS
SELECT d.id, d.work_center_id, w.name AS work_center, w.branch_code, coalesce(b.name, w.branch_code) AS plant,
       d.event_date, d.minutes, d.reason
FROM mfg.downtime d
JOIN mfg.work_centers w ON w.id = d.work_center_id
LEFT JOIN core.branches b ON b.code = w.branch_code;
