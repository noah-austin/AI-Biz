# Business Rulebook: Bramblewood Industrial Supply (demo)

*Fictional company. The code that applies these rules is `kit/metrics.py`, `kit/schema/050_views.sql`,
`055_ops_views.sql`, `056_orders_views.sql` and `kit/cleanup.py`.*

## 1. Systems
| System | Objects synced | How often |
|---|---|---|
| CRM | Users, accounts, opportunities (quotes, project bids, supply agreements), field history | Hourly |
| ERP: orders and shipping | Orders, order lines (ordered, first shipment, shipped, price, cost) | Hourly |
| Accounting | Customers, invoices (one per shipped order, Reference = "SO" + order number) | Hourly |
| Inventory | Items, warehouses, stock on hand, count corrections | Hourly |
| Purchasing | Vendors, purchase orders, lines | Hourly |
| HR and payroll | Employees, licenses, weekly timesheets, open roles | Hourly |

Sales are billed from shipped orders, not from CRM deals, so the "won deal with no invoice" check is switched off.

## 2. Rules that apply everywhere
The same as every install: time zone America/Chicago, calendar fiscal year, weighted percentages, missing values left out
rather than counted as zero, and year-to-date compared with the same dates last year.

## 3. Branches
| Code | Name | Region |
|---|---|---|
| HOU-01 | Houston | Gulf Coast |
| BMT-06 | Beaumont | Gulf Coast |
| SAT-03 | San Antonio | South Texas |
| CRP-05 | Corpus Christi | South Texas |
| DAL-02 | Dallas | North & Central |
| AUS-04 | Austin | North & Central |

## 4. Metrics
- **Sales (orders):** value of what shipped, at the order price, by order date. Backorders count when they ship.
- **Gross margin:** (sales − cost of what shipped) ÷ sales, for orders placed in the period. Cost is the item cost on the order.
- **Fill rate:** order lines whose first shipment carried the whole quantity ÷ order lines, orders placed in the period.
- **Shipped on time:** orders whose first shipment left on or before the date the customer asked for ÷ orders shipped.
- **Backorders:** what's still owed on orders that have already shipped once, at the order price. New orders not yet shipped aren't backorders.
- **Inventory turns:** cost of what shipped in the last 12 months ÷ today's inventory value.
- **Bookings, win rate, pipeline** (CRM quotes and agreements), **billed, collected, receivables** and the **people**,
  **inventory** and **purchasing** measures follow the standard definitions (see Bluestem's rulebook).

## 5. Goals (weekly unless noted)
| Metric | Goal |
|---|---|
| Bookings for 2026 (CRM) | $22.0M |
| Bookings | $400K |
| New pipeline | $1.2M |
| New deals | 20 |
| Billed, past 31 days | $3.4M |
| Collected | $750K |
| AR over 60 days | $1.0M or less |
| Win rate by $, trailing 90 days | 35% |
| Fill rate | 94% |
| Shipped on time | 85% |
| Gross margin on orders | 24% |
| Overtime, % of hours worked | 8% or less |

## 6. Alert rules
As standard, except late-invoice alerts only for unpaid balances of $5K or more (Bramblewood sends thousands of small
invoices). Plus: a branch whose fill rate last week was under 90% (with at least 50 lines).
