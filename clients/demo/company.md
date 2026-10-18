# Bluestem Facility Services (fictional demo company)

**Everything here is made up.** Bluestem is the company we show prospects so they can see the hub working on realistic data without anyone's real numbers.

## The story
- Commercial facility services in Texas: HVAC, electrical and building systems. Repairs, yearly service contracts and replacement projects.
- About 250 people and 6 branches in 3 regions:
  - North Texas: Dallas, Fort Worth;
  - Central Texas: Austin, San Antonio;
  - Gulf Coast: Houston, Houston South.
- Around $20–25M a year in new sales and 600+ customer accounts: hospitals, school districts, offices, industrial sites, retail, and local government.
- Systems: a CRM (Salesforce-style) and an accounting system (QuickBooks-style). Before the hub, the VP of Sales built a weekly spreadsheet by hand, and finance chased late invoices from an aging report.

## Problems planted in the data (what the clean-up list finds)
- Won deals with a placeholder close date in 2111, so they're missing from bookings.
- Duplicate deals that double-count pipeline.
- Open deals whose close date passed months ago.
- One branch (Houston South) left margin blank on most 2025 wins.
- Lost deals with no loss reason.
- Won deals that were never invoiced (or the invoice doesn't reference the deal).
- Accounting customers not linked to a CRM account, and customer names that don't match between systems.
- A few slow payers and disputed invoices sitting 90+ days late.

## The data moves
`generate.py` produces the systems as they'd look on any given day. Run it daily (and then the sync) and the company "lives": new deals appear, deals close, invoices get paid. The history and "last 7 days" views then behave as they would at a real client.

## A 10-minute demo script
1. **Home ("Where we stand").** "This is your Monday meeting, already done." Click a tile: every number opens the deals behind it, and every deal opens in the CRM.
2. **Last 7 days.** "Your CRM forgets what changed. We keep the history, so you can see what moved."
3. **Scorecard.** "If you run EOS or any weekly scorecard: this fills itself in. Nobody types it on Monday morning."
4. **Win / loss → Where we sell best.** "Industrial projects and healthcare service contracts are where you win the most money. Here's the proof, and every cell clicks through."
5. **Receivables → Who to call first.** CRM and accounting joined: "Sales and finance looking at the same customer."
6. **Data checks (in passing).** "As a side benefit, it flags records that look wrong in your systems, linked to each one." Mention it and move on; it isn't the pitch.
7. **Branch view.** Sign in as a branch manager: they see only their branches.
8. **Ask AI.** "Ask it questions in plain English. It reads the same numbers, follows the same rules, and can't change anything."
9. **Forecast.** "Your forecast spreadsheet, replaced." Change a few calls and watch the totals move. Admins' calls are saved with who changed what; a guest's are not.
10. **Alerts.** "These would have reached your phone this week." Point at the rules on the right: set with each client.
11. **AI agents.** The daily brief, payment reminders waiting for approval (nothing is ever sent from the demo), the weekly update draft and prep for the biggest meeting. In the demo they are prepared by rules from Bluestem's data; in a live install the agents write them.

Visitors who arrive from the website's "See a live demo" button sign in as a guest and see a short "Welcome to the demo" card; the banner links back to the website to book a call.
