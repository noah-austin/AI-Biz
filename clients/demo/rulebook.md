# Business Rulebook: Bluestem Facility Services (demo)

*Fictional company. This shows what a client's rulebook looks like when it's filled in. The code that applies these rules is `kit/metrics.py`, `kit/schema/050_views.sql`, `kit/schema/055_ops_views.sql` and `kit/cleanup.py`.*

## 1. Systems
| System | Objects synced | How often |
|---|---|---|
| CRM | Users, accounts, opportunities, opportunity field history | Hourly |
| Accounting | Customers, invoices (with paid date) | Hourly |
| Field service | Jobs (work orders), parts used on jobs | Hourly |
| Inventory | Parts, locations (warehouses and van stock), stock on hand, count corrections | Hourly |
| Purchasing | Vendors, purchase orders, order lines | Hourly |
| HR and payroll | Employees, licenses and certifications, weekly timesheets, open roles | Hourly |

The CRM is the source for sales; accounting is the source for billing and cash; the field-service app for jobs; inventory for stock; purchasing for orders and vendor spend; HR and payroll for people and hours. Invoices link to deals through the invoice's **Reference** field (the deal ID), and to accounts through the customer's **CRM Account ID**.

## 2. Rules that apply everywhere
- Deals with **Exclude From Reporting** ticked (internal and training records) are never counted anywhere.
- Time zone: **America/Chicago**. "Today" and all dates are Central time.
- Fiscal year = calendar year.
- Percentages are weighted (total won ÷ total closed), never averaged.
- Missing margin is left out of margin %, not counted as 0%.
- Year-to-date compares Jan 1 to today with Jan 1 to the same date last year.

## 3. Branches
| CRM code | Name | Region |
|---|---|---|
| DAL-01 | Dallas | North Texas |
| FTW-02 | Fort Worth | North Texas |
| AUS-03 | Austin | Central Texas |
| SAT-04 | San Antonio | Central Texas |
| HOU-05 | Houston | Gulf Coast |
| HOU-06 | Houston South | Gulf Coast |

An invoice's branch comes from its deal; if it has no deal reference, from the customer's CRM account.

## 4. Metrics
- **Bookings:** total amount of Closed Won deals, by close date.
- **Win rate by $:** won amount ÷ (won + lost amount) for deals closed in the period. **By count:** the same with the number of deals. Open deals don't count. Both are shown, because they tell different stories.
- **Margin %:** total margin dollars ÷ total amount, for won deals that have a margin entered.
- **Open pipeline:** open deals, by expected close date. **Weighted** = amount × stage probability (Prospecting 10%, Qualification 20%, Proposal 50%, Negotiation 75%). Deals whose close date has passed are reported separately as "past due".
- **New pipeline:** deals created in the period, whatever happened to them since.
- **Billed:** invoices dated in the period. **Collected:** payments by paid date. On the scorecard, billing covers the past 31 days, because service contracts bill on the 1st and single weeks swing a lot.
- **Receivables aging:** unpaid balance by days past due: Current, 1–30, 31–60, 61–90, 90+.
- **AR over 60 days (scorecard):** unpaid balance more than 60 days past due at the end of each week, rebuilt from invoice and paid dates. Accounting gives one paid date per invoice, so payments are treated as paid in full.
- **Where we sell best:** among slices with 5+ closed deals and a close rate above the overall rate, the ones with the most dollars won. Ranking by rate alone puts tiny 100%-win slices on top.
- **Last 7 days:** from CRM field history: deals created, won and lost, and open deals whose close date was pushed into a later month.

### Field service
- **Jobs completed:** jobs marked Completed, by completion date. Canceled jobs don't count.
- **Emergency calls on time:** emergency calls reached within 4 hours of the call coming in ÷ emergency calls reached, by arrival date. Urgent calls have a 24-hour promise; routine jobs are on time if done on their scheduled day.
- **First-time fix:** 100% minus return visits as a share of repairs, counting both in the same period (return visits ÷ repairs completed, not counting the return visits themselves). Counting both in the same period means recent weeks don't look better just because their return visits haven't happened yet.
- **Technician utilization:** hours on completed jobs ÷ hours worked (regular + overtime, from payroll), technicians only, last 4 complete weeks.
- **Completed, not invoiced:** billable jobs (repairs and installs) finished more than 14 days ago with no invoice number. Maintenance visits are covered by the contract.

### Inventory
- **Inventory value:** on hand × standard cost, every warehouse and van. Negative balances count as zero; parts with no standard cost are left out (and listed in Data checks).
- **Turns:** cost of parts used on jobs in the last 12 months ÷ today's inventory value.
- **Below reorder point:** warehouse stock at or below its reorder point; vans are restocked from the warehouse. Critical parts (refrigerant, capacitors, contactors, condenser fan motors) are listed first.
- **Dead stock:** on hand but not used on a job in 180 days.
- **Shrinkage:** count and damage corrections in the last 90 days at standard cost; negative means stock went missing.

### Purchasing
- **Spend:** purchase orders placed in the last 12 months, by order date, excluding canceled orders.
- **On-time delivery:** orders received on or before their expected date ÷ orders received, last 90 days. Orders with no expected date are left out.
- **Received, not billed:** orders received more than 30 days ago with no vendor bill yet.
- **Price change:** per part, the quantity-weighted average price in the last 90 days against the same 90 days a year earlier, for parts bought in both periods.

### People
- **Headcount:** people on payroll today (hired on or before today, not past their last day).
- **Turnover:** people who left in the last 12 months ÷ average headcount (the average of the 12 month-end counts).
- **Overtime:** overtime hours ÷ hours worked (regular + overtime), hourly staff, last 4 complete weeks.
- **Licenses:** expired, or expiring within 30 days, for people on payroll. Pay rates and personal details are never brought into the hub.

## 5. Goals (2026)
| Metric | Goal |
|---|---|
| Bookings for the year | $26.0M |
| Weekly bookings | $500K |
| Weekly new pipeline | $1.3M |
| Weekly new deals | 25 |
| Billed, past 31 days | $1.9M |
| Weekly collected | $450K |
| Win rate by $, trailing 90 days | 36% |
| AR over 60 days | $400K or less |
| Emergency calls reached in 4 hours (weekly) | 90% |
| First-time fix (weekly) | 85% |
| Overtime, % of hours worked (weekly) | 8% or less |

## 6. Known data problems
See the hub's **Data checks** page for the live list: placeholder close dates, duplicates, stale open deals, missing margins (mostly Houston South, 2025), lost deals without reasons, won deals with no invoice, customers not linked to the CRM, completed jobs not invoiced, jobs booked to people who have left, technicians on an expired license, missing timesheets, staff with no manager, negative stock, parts with no cost, received orders with no vendor bill, and a duplicate vendor.

## 7. Alert rules (operations)
Emergency call reached 8+ hours late; a critical part out at a warehouse (urgent); an open purchase order of $5K+ past its expected date; a license expiring within 30 days (expired is urgent); a branch's weekly overtime above 15% of hours worked.
