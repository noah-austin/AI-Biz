# Business Rulebook: Kestrel Ridge Engineering (demo)

*Fictional company. The code that applies these rules is `kit/metrics.py`, `kit/schema/050_views.sql`,
`055_ops_views.sql`, `057_projects_views.sql` and `kit/cleanup.py`.*

## 1. Systems
| System | Objects synced | How often |
|---|---|---|
| CRM | Users, accounts, opportunities (proposals), field history | Hourly |
| Projects and time | Projects (billing type, fee, budget hours, percent complete), weekly time by person and project | Hourly |
| Accounting | Customers, invoices (monthly per project, Reference = the project's CRM deal) | Hourly |
| HR and payroll | Employees, licenses, weekly timesheets (hourly staff), open roles | Hourly |

## 2. Offices
| Code | Name | Region |
|---|---|---|
| HOU | Houston | Gulf Coast |
| DFW | Dallas | North Texas |
| AUS | Austin | Central Texas |
| SAT | San Antonio | Central Texas |

## 3. Metrics
- **Billable utilization:** billable hours ÷ all hours recorded (billable and internal, not time off), for everyone who
  records time to projects. Target 75%.
- **Realization:** for projects completed in the last 12 months, amount billed ÷ standard value of the hours spent
  (hours × standard rates). Below 100% means write-downs, or fixed fees outrun by the hours.
- **Project margin:** for the same projects, (billed − cost of the hours) ÷ billed.
- **Unbilled work in progress:** billable hours on hourly projects not yet invoiced, at standard rates, from before this month.
- **Backlog:** contract value minus billed to date, for projects not finished.
- **Over pace:** a fixed-fee project whose budget hours used are more than 20 points ahead of its percent complete.
- **Billed, collected, receivables, bookings, win rate, pipeline** and **people** measures follow the standard definitions
  (see Bluestem's rulebook). Engineers are the frontline; their Professional Engineer license is the one that matters.

## 4. Goals (weekly unless noted)
| Metric | Goal |
|---|---|
| Bookings for 2026 | $17.0M |
| Bookings | $330K |
| New pipeline | $900K |
| New deals | 10 |
| Billed, past 31 days | $1.5M |
| Collected | $340K |
| AR over 60 days | $600K or less |
| Win rate by $, trailing 90 days | 36% |
| Billable utilization | 75% |
| Overtime, % of hours worked | 8% or less |

## 5. Alert rules
Standard, plus: an office whose billable utilization last week was under 65%, and a fixed-fee project past its budget hours.
