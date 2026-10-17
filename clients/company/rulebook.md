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
- **Goal:** $90,000 in year one. "Pace" is the goal × the share of the year gone so far.

## Time
- **Weeks** run Monday to Sunday. Target: 20 hours a week.
- Time not tied to a company counts as "Running the business".

## Rules
- Prospects and companies are archived, never deleted. Time entries and expenses can be deleted (with a confirmation), because mistakes there are common and harmless.
- Client data never goes into this hub. Only our own relationships, time and money.
