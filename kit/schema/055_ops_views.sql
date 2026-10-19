-- Analytical views for the operations systems. Business rules live here once, and the client's
-- rulebook says the same in words. They join core.branches directly (not rpt.branches) so
-- re-creating the sales views in 050 never drops these.
DROP VIEW IF EXISTS rpt.employees, rpt.certifications, rpt.timesheets, rpt.jobs, rpt.part_usage, rpt.stock,
    rpt.purchase_orders, rpt.po_lines CASCADE;

-- One row per person on payroll, past and present. Active = not yet past their termination date.
-- Frontline = the department set as [people] frontline_department in config.toml (technicians, drivers, crews...).
CREATE VIEW rpt.employees AS
SELECT e.id, e.name, e.email, e.title, e.department, e.branch_code,
       coalesce(b.name, e.branch_code) AS branch, coalesce(b.region, 'Unmapped') AS region,
       e.hire_date, e.termination_date, e.termination_type, e.manager_id, m.name AS manager_name, e.pay_type,
       (e.termination_date IS NULL OR e.termination_date >= core.local_today()) AS is_active,
       (e.department = coalesce((SELECT value FROM core.settings WHERE key = 'frontline_department'), 'Field Service')) AS is_frontline
FROM hr.employees e
LEFT JOIN hr.employees m ON m.id = e.manager_id
LEFT JOIN core.branches b ON b.code = e.branch_code;

-- Certifications and licenses. Expiring = runs out within 30 days; no expiry date means it doesn't expire.
CREATE VIEW rpt.certifications AS
SELECT c.id, c.employee_id, e.name AS employee_name, e.title, e.branch_code, e.branch, e.is_active,
       c.name AS certification, c.issued_date, c.expires_date,
       c.expires_date - core.local_today() AS days_left,
       (c.name = (SELECT value FROM core.settings WHERE key = 'license')) AS is_license,
       CASE WHEN c.expires_date IS NULL THEN 'No expiry'
            WHEN c.expires_date < core.local_today() THEN 'Expired'
            WHEN c.expires_date <= core.local_today() + 30 THEN 'Expiring'
            ELSE 'Valid' END AS status
FROM hr.certifications c JOIN rpt.employees e ON e.id = c.employee_id;

-- Weekly hours from payroll. Worked = regular + overtime; paid time off is not time worked.
CREATE VIEW rpt.timesheets AS
SELECT t.id, t.employee_id, e.name AS employee_name, e.department, e.is_frontline, e.branch_code, e.branch,
       t.week_start, t.regular_hours, t.overtime_hours, t.pto_hours,
       t.regular_hours + t.overtime_hours AS worked_hours, t.approved
FROM hr.timesheets t JOIN rpt.employees e ON e.id = t.employee_id;

-- One row per field-service job. Response = arrival minus when the call came in.
-- On time: Emergency within 4 hours, Urgent within 24 hours, Routine on its scheduled day.
-- fixed_first_time: a completed repair (not itself a return visit) with no return visit logged against it (per job;
-- the first-time fix rate itself is worked out from return visits in kit/metrics.py).
CREATE VIEW rpt.jobs AS
SELECT w.id, w.number, w.account_id, a.name AS account_name, a.segment,
       w.branch_code, coalesce(b.name, w.branch_code) AS branch, coalesce(b.region, 'Unmapped') AS region,
       w.job_type, w.priority, w.status, w.technician_id, t.name AS technician_name, t.is_active AS technician_active,
       w.created_at, w.scheduled_date, w.arrived_at, w.completed_at,
       (w.arrived_at AT TIME ZONE core.client_tz())::date AS arrived_date,
       (w.completed_at AT TIME ZONE core.client_tz())::date AS completed_date,
       round(extract(epoch FROM (w.arrived_at - w.created_at)) / 3600.0, 2) AS response_hours,
       CASE w.priority WHEN 'Emergency' THEN 4 WHEN 'Urgent' THEN 24 END AS sla_hours,
       CASE WHEN w.arrived_at IS NULL THEN NULL
            WHEN w.priority = 'Emergency' THEN w.arrived_at <= w.created_at + interval '4 hours'
            WHEN w.priority = 'Urgent' THEN w.arrived_at <= w.created_at + interval '24 hours'
            ELSE (w.arrived_at AT TIME ZONE core.client_tz())::date <= w.scheduled_date END AS on_time,
       w.labor_hours, w.billable, w.billable_amount, w.invoice_number, w.is_callback, w.parent_id,
       (w.status IN ('Scheduled', 'In progress')) AS is_open,
       CASE WHEN w.status = 'Completed' AND w.job_type = 'Repair' AND NOT w.is_callback
            THEN NOT EXISTS (SELECT 1 FROM fsm.work_orders c WHERE c.parent_id = w.id AND c.is_callback) END AS fixed_first_time
FROM fsm.work_orders w
LEFT JOIN crm.accounts a ON a.id = w.account_id
LEFT JOIN rpt.employees t ON t.id = w.technician_id
LEFT JOIN core.branches b ON b.code = w.branch_code;

-- Parts used on jobs, valued at today's standard cost (parts with no cost are left out of dollar figures).
CREATE VIEW rpt.part_usage AS
SELECT p.id, p.work_order_id, p.sku, i.description, i.category, p.qty, p.location_id, l.branch_code,
       coalesce(b.name, l.branch_code) AS branch, p.used_date, p.qty * i.standard_cost AS cost
FROM fsm.work_order_parts p
LEFT JOIN inv.items i ON i.id = p.sku
LEFT JOIN inv.locations l ON l.id = p.location_id
LEFT JOIN core.branches b ON b.code = l.branch_code;

-- Stock by location. Value = on hand × standard cost, never below zero.
-- Below reorder point: warehouses only (vans are restocked from the warehouse).
-- Dead stock: on hand but not used on a job in 180 days.
CREATE VIEW rpt.stock AS
SELECT s.id, s.location_id, l.name AS location, l.kind AS location_kind, l.branch_code,
       coalesce(b.name, l.branch_code) AS branch, s.sku, i.description, i.category, i.critical, i.preferred_vendor_id,
       v.name AS vendor, i.standard_cost, s.on_hand, s.reorder_point, s.reorder_qty,
       greatest(s.on_hand, 0) * i.standard_cost AS value,
       (l.kind = 'Warehouse' AND s.reorder_point > 0 AND s.on_hand <= s.reorder_point) AS below_reorder,
       (s.on_hand > 0 AND (s.last_issued_date IS NULL OR s.last_issued_date < core.local_today() - 180)) AS is_dead,
       s.last_issued_date, s.last_counted_date
FROM inv.stock s
JOIN inv.locations l ON l.id = s.location_id
LEFT JOIN inv.items i ON i.id = s.sku
LEFT JOIN ap.vendors v ON v.id = i.preferred_vendor_id
LEFT JOIN core.branches b ON b.code = l.branch_code;

-- Purchase orders. On time = received on or before the expected date. Late (open) = expected date has passed.
CREATE VIEW rpt.purchase_orders AS
SELECT p.id, p.number, p.vendor_id, v.name AS vendor, v.category AS vendor_category,
       p.branch_code, coalesce(b.name, p.branch_code) AS branch, p.kind, p.ordered_date, p.expected_date,
       p.received_date, p.status, p.amount, p.billed_amount, p.deal_id,
       (p.status = 'Open') AS is_open,
       CASE WHEN p.received_date IS NOT NULL AND p.expected_date IS NOT NULL THEN p.received_date <= p.expected_date END AS on_time,
       CASE WHEN p.received_date IS NOT NULL THEN greatest(0, p.received_date - p.expected_date)
            WHEN p.status = 'Open' THEN greatest(0, core.local_today() - p.expected_date) END AS days_late
FROM ap.purchase_orders p
LEFT JOIN ap.vendors v ON v.id = p.vendor_id
LEFT JOIN core.branches b ON b.code = p.branch_code;

CREATE VIEW rpt.po_lines AS
SELECT l.id, l.po_id, p.number AS po_number, p.vendor_id, p.vendor, p.branch_code, p.branch, p.ordered_date, p.status,
       l.sku, coalesce(i.description, l.description) AS description, l.qty, l.unit_price, l.qty * l.unit_price AS amount
FROM ap.po_lines l JOIN rpt.purchase_orders p ON p.id = l.po_id
LEFT JOIN inv.items i ON i.id = l.sku;
