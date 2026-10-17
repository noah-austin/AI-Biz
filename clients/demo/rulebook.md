# Business Rulebook: Bluestem Facility Services (demo)

*Fictional company. This shows what a client's rulebook looks like when it's filled in. The code that applies these rules is `kit/metrics.py`, `kit/schema/050_views.sql` and `kit/cleanup.py`.*

## 1. Systems
| System | Objects synced | How often |
|---|---|---|
| CRM | Users, accounts, opportunities, opportunity field history | Hourly |
| Accounting | Customers, invoices (with paid date) | Hourly |

The CRM is the source for sales; accounting is the source for billing and cash. Invoices link to deals through the invoice's **Reference** field (the deal ID), and to accounts through the customer's **CRM Account ID**.

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

## 6. Known data problems
See the hub's **Clean-up** page for the live list: placeholder close dates, duplicates, stale open deals, missing margins (mostly Houston South, 2025), lost deals without reasons, won deals with no invoice, and customers not linked to the CRM.
