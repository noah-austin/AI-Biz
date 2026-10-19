# Business Rulebook: Cottonwood Precision Manufacturing (demo)

*Fictional company. The code that applies these rules is `kit/metrics.py`, `kit/schema/050_views.sql`,
`055_ops_views.sql`, `056_orders_views.sql`, `059_production_views.sql` and `kit/cleanup.py`.*

## 1. Systems
| System | Objects synced | How often |
|---|---|---|
| CRM | Users, accounts, opportunities (quotes, blanket orders), field history | Hourly |
| ERP: orders and shipping | Customer orders and lines | Hourly |
| Shop floor (MES) | Work centers, production orders, downtime events | Hourly |
| Inventory | Items (finished goods and raw materials), stockrooms, stock on hand, count corrections | Hourly |
| Purchasing | Vendors, purchase orders, lines | Hourly |
| Accounting | Customers, invoices (one per shipped order) | Hourly |
| HR and payroll | Employees, certifications, weekly timesheets, open roles | Hourly |

## 2. Plants
| Code | Name | Region |
|---|---|---|
| FTW | Fort Worth | North Texas |
| WAC | Waco | Central Texas |

## 3. Metrics
- **Production on time:** production orders completed on or before their due date ÷ production orders completed.
- **Scrap rate:** units scrapped ÷ (units completed + scrapped).
- **Labor efficiency:** standard hours ÷ actual hours on completed production orders.
- **Machine effectiveness (OEE):** availability × performance × quality, last 30 days. Availability = hours running ÷
  (hours running + downtime); performance = standard hours earned ÷ hours running; quality = good ÷ all units made.
  Idle time with no work booked doesn't count against a machine.
- **Downtime:** minutes logged by work centers, by reason; changeovers and planned maintenance are expected.
- **Orders, inventory, purchasing, people** and CRM/accounting measures follow the standard definitions (see Bramblewood's
  and Bluestem's rulebooks). Production staff are the frontline; the welder certification is the one that matters.

## 4. Goals (weekly unless noted)
| Metric | Goal |
|---|---|
| Bookings for 2026 (CRM) | $9.5M |
| Bookings | $200K |
| New pipeline | $550K |
| Billed, past 31 days | $3.2M |
| Collected | $740K |
| AR over 60 days | $950K or less |
| Win rate by $, trailing 90 days | 34% |
| Production orders on time | 90% |
| Scrap rate | 2.5% or less |
| Fill rate | 92% |
| Shipped on time | 80% |
| Gross margin on orders | 27% |
| Overtime, % of hours worked | 12% or less |

## 5. Alert rules
Standard, with late-invoice alerts from $10K. Plus: a work center down 4+ hours in a day for a breakdown.
