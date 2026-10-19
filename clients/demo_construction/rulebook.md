# Business Rulebook: Mesquite Ridge Constructors (demo)

*Fictional company. The code that applies these rules is `kit/metrics.py`, `kit/schema/050_views.sql`,
`055_ops_views.sql`, `058_jobcost_views.sql` and `kit/cleanup.py`.*

## 1. Systems
| System | Objects synced | How often |
|---|---|---|
| CRM | Users, accounts, opportunities (bids), field history | Hourly |
| Job cost | Jobs (contract, budget, estimate at completion), change orders, monthly costs by category, pay applications | Hourly |
| Accounting | Customers, invoices (one per pay application net of retainage, plus retainage releases) | Hourly |
| Purchasing | Vendors, subcontracts, materials and rental orders | Hourly |
| HR and payroll | Employees, certifications, weekly timesheets, open roles | Hourly |

## 2. Offices
| Code | Name | Region |
|---|---|---|
| HOU | Houston | Gulf Coast |
| SAT | San Antonio | Central Texas |
| AUS | Austin | Central Texas |

## 3. Metrics (the work-in-progress schedule)
All as of the end of last month, the way contractors close the books.
- **Contract:** original contract + approved change orders.
- **Percent complete:** cost to date ÷ estimated cost at completion (cost-to-cost).
- **Earned:** percent complete × contract. **Backlog:** contract − earned, on jobs not finished.
- **Over/(under) billed:** billed to date − earned. Over-billed is a liability; under-billed means financing the owner.
- **Margin at bid:** (original contract − budget cost) ÷ original contract. **Projected:** (contract − estimate at completion) ÷ contract.
  **Fade** = bid − projected.
- **Retainage held:** retainage withheld on pay applications and not yet released.
- **Change orders waiting:** submitted to owners and not yet signed.
- The **people**, **purchasing** and CRM/accounting measures follow the standard definitions (see Bluestem's rulebook).
  Field crew are the frontline; the crane operator certification is the one that matters.

## 4. Goals (weekly unless noted)
| Metric | Goal |
|---|---|
| Bookings for 2026 | $95M |
| Bookings | $1.8M |
| New pipeline | $6.0M |
| New bids | 4 |
| Billed, past 31 days | $7.2M |
| Collected | $1.6M |
| AR over 60 days | $3.2M or less |
| Win rate by $, trailing 90 days | 30% |
| Overtime, % of hours worked | 12% or less |

## 5. Alert rules
Standard, except: no mid-month billing-pace alert (pay applications go out monthly) and late-invoice alerts only from $25K.
Plus: an active job projected to lose money (urgent), and a job under-billed by more than $250K.
