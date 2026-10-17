# Rulebook: our own company hub

How each number in the practice tracker is counted. The code is `kit/practice/metrics.py`; change both together.

## Pipeline
- **Prospect stages:** Lead → Contacted → Conversation → Proposal sent → Won, or Lost / Not now.
- **Weighted pipeline** = estimated first-year value × stage probability: Lead 5%, Contacted 10%, Conversation 25%, Proposal 50%.
- **Estimated first-year value** = what the company would pay in its first year if it closes (entry offer + build + 12 months of retainer, as best guessed).
- **Conversations this month** = calls and meetings logged this calendar month, with anyone (prospects, partners, clients). Target: 15.
- **What's working** groups every prospect and client by how we met them, and counts how many reached a conversation and how many were won.
- Logging an activity with stage "Won" turns a prospect into a client. An engagement set to Active does the same.

## Money
- **Revenue** = invoices issued, by issue date, paid or not. (The invoices themselves are sent from the invoicing tool; the hub records them.)
- **Cash** = invoices paid, by paid date.
- **Monthly recurring (MRR)** = monthly fees of retainer engagements that are active today.
- **Profit** = revenue − expenses, for the same period.
- **Effective hourly rate** = revenue this year ÷ all hours logged this year, billable or not.
- **Goal:** $100,000 of revenue between Oct 1, 2026 and Sep 30, 2027 (invoices issued in that window). "Pace" is the goal × the share of the window gone so far.
- **Forecast** = revenue so far + active retainers' monthly fees × the full months left + the weighted pipeline.
- **Needed per month** = what's left to the goal ÷ the months left, including this one.
- **Referral fees** = 10% of a referred client's invoices in their first 12 months.

## My weekly scorecard (Monday to Sunday)
| Measure | Counted as | Weekly target |
|---|---|---|
| Outreach | Activities logged as Email or LinkedIn | 25 |
| New prospects | Prospect companies added | 25 |
| Conversations | Activities logged as Call or Meeting | 4 |
| Proposals | Engagements created | 1 |
| Hours | All time logged | 20 |

## Time
- **Weeks** run Monday to Sunday. Target: 20 hours a week.
- Time not tied to a company counts as "Running the business".

## Agents
- Three agents work for the business: **Business development**, **Social media manager** and **Chief of staff**. Their jobs and schedules are on the Agents page (`kit/agents/registry.py`).
- Everything they produce waits in the **Inbox**. Approving a prospect adds it to the pipeline as a Lead, with a drafted first message. "I sent it" on a message logs the email or LinkedIn activity and moves a Lead to Contacted.
- They never send, post or delete anything; they use public web information only and never open LinkedIn; they never name clients in posts.
- Cost: every call is logged; each run has its own limit; all agents share the monthly cap ($60 to start).

## Rules
- Prospects and companies are archived, never deleted. Time entries and expenses can be deleted (with a confirmation), because mistakes there are common and harmless.
- Client data never goes into this hub. Only our own relationships, time and money.
