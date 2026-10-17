# The concept, v2

*2026-10-17. Replaces v1 (still in git history). A working document: change it as real conversations teach us.*

## 1. What the business is

**We help mid-size companies run on their data: one trusted set of numbers, the tools to act on it, and AI that actually works because the data underneath is right.**

Data consolidation is the engine and the reason everything works. It isn't the headline. Buyers don't wake up wanting "data consolidation"; they want:
- a Monday meeting where nobody argues about whose number is right;
- reports that build themselves instead of eating an analyst's week;
- to know early when a big deal slips or a customer stops paying;
- AI that gives real answers about *their* business, not generic ones.

## 2. How it works: platform, method, custom plan

Like a good Salesforce consultant, we bring three things:

| | What it is | Why it matters |
|---|---|---|
| **A platform** | The kit (`kit/`): sync from their systems, one database they own, business rules, a web hub, an AI layer. | We don't start from zero, so builds take weeks, not months. It runs for about $6 a month on a server the client owns. |
| **A method** | Understand the business → write the rulebook → connect the data → reproduce their existing reports to the cent → build what they need most → keep it trusted. | Reliable results, and numbers people trust because they've seen them match. |
| **A custom plan** | Which systems, which numbers, which tools and which AI uses matter most to *this* client. | Every company's pain is different. The plan is tailored; the platform and method stay the same. |

## 3. What we offer

### The menu (tailored per client, all built on the same data foundation)
- **Trusted numbers:** a single source of truth, the business rulebook, and a clean-up list that gets source data fixed.
- **Run the business on it:**
  - a self-filling weekly scorecard;
  - a monthly business review the AI drafts;
  - help setting up the meeting rhythm itself: who owns each number and how the meetings run.
- **Tools:** dashboards, a tool that replaces their key spreadsheet, drill-downs to every record, branch- and role-level access.
- **Push, not pull:** scheduled emails and Teams messages, plus alerts like "a $400K deal slipped" or "a customer passed 90 days late".
- **AI:**
  - an "Ask AI" assistant over their own data;
  - daily insights;
  - document drafting such as proposals and summaries;
  - a secure read-only connection so Copilot, ChatGPT or Claude can use the same trusted data.

### What we don't do
These limits keep the business focused:
- implementing or replacing ERPs and CRMs (we work alongside their consultant);
- AI that isn't connected to their data;
- training custom AI models;
- writing back into their systems without explicit sign-off.

### How they buy (prices are starting points to test)
| Step | What it is | Length | Price |
|---|---|---|---|
| **CRM Health Report** (entry offer) | Read-only connection to their CRM; the kit's checks show the wins their reports can't see and the exact records to fix. | ~1 week | $1,500–2,500 |
| **Assessment** | Systems, key reports, users, biggest pain, and a written custom plan. Credited toward the build. | ~2 weeks | $3,500–5,000 |
| **Foundation + first tools** | Connect 2–3 systems, the rulebook, reproduce their reports, then the 2–3 things from the plan that matter most. | 4–6 weeks | $15,000–30,000 |
| **Run & Grow** (monthly) | Monitoring, backups, fixes, new tools and new AI uses each month, and a monthly review with leadership. | Ongoing | $1,500–4,000 / month |

The server and AI usage are billed to the client's own accounts, with no markup.

**Founding-client deal (first 1–2 clients):**
- a discount, in exchange for a case study and a reference;
- a guarantee: if we can't reproduce their key report to the cent, the Assessment is free.

## 4. Why this beats being a general AI consultant
- **General AI consulting is crowded and vague.** In 2026 everyone is an "AI consultant". The work tends to be workshops, strategy decks and one-off automations, which are hard to differentiate and hard to price.
- **Most AI projects fail because the data is a mess.** We fix that first, so our AI works.
- **A data foundation brings recurring revenue.** Once leadership runs its meeting on it, the monthly fee lasts for years. One-off AI projects end.
- **The market is big enough.** There are roughly 200,000 mid-size US companies ($10M–$1B in revenue), and most have scattered data and no data team. We need 5–10 clients.
- **Noah's edge:** he's an operator (COO / chief of staff) selling to operators. A tech shop can't sell "your meeting runs on one set of numbers" with the same credibility.

## 5. Who we sell to
- **Buyer:** COO, CFO, owner or president of a company with 50–1,000 people, with a CRM and an accounting system, and no data team.
- **Pain signals:** leadership numbers built by hand in Excel; reports that don't match; a new CRM nobody trusts; "we bought Copilot and it can't answer anything".
- **Niche (open question):** we take any good-fit client. The leading guess for where to aim marketing is **contractors and field-service companies** (construction, mechanical, HVAC, facilities):
  - the case study and the demo are already there;
  - they run on the same few systems (Salesforce or HubSpot, Procore, Sage or QuickBooks);
  - they gather in trade associations (AGC, ABC, MCAA).

  We decide after 15–20 conversations show who responds best.

## 6. Getting the first clients (no warm network)
1. **15–20 conversations in the next month** with COOs, CFOs and owners. Ask what's painful, what they've tried, and what they'd pay to fix. These calls are market research and pipeline at the same time.
2. **Referral partners:** fractional CFOs and COOs, CPA firms, IT providers, and CRM consultants. Offer a referral fee of about 10% of first-year fees.
3. **The live demo** (Bluestem) plus the case story: built in 9 days, runs for $6 a month. The company can be named; its figures stay out.
4. **LinkedIn as an operator, not a vendor:** short posts like the 2111 close dates, "never average percentages", and "your CRM's AI only sees your CRM".
5. **Local groups:** Vistage and EO chapters, chambers of commerce, trade associations. A 20-minute talk: "What AI can actually do with your company's data."
6. **Pitch the AI-readiness angle:** "Before you roll out Copilot, make your data right for it."

## 7. Building the business, not just the software

**Stop adding features until a client needs them.** The demo is good enough to sell. The first client decides the next connector and the next tool. In the next 60 days, about 70% of the time goes to selling.

**Must-haves before client #1:**
- [ ] Microsoft sign-in (Google too if the client needs it)
- [ ] Alerts when a sync or backup fails
- [ ] A one-command installer, so every client runs the same kit
- [ ] Contracts: master services agreement, statement of work, data terms (including that data goes to Anthropic's API, which doesn't train on it)
- [ ] One-page security summary, plus standard answers to IT questionnaires
- [ ] Insurance: professional liability (E&O) plus cyber
- [ ] The connector client #1 actually needs

**To scale on 20 hours a week (soon after):**
- **One product, many installs.** Clients only differ by settings and their own small client folder; updates go to everyone.
- **A dashboard for Noah** showing the health of every client install on one screen.
- **Open-source connectors (dlt)** for the long tail of systems, plus a spreadsheet upload for quick wins.
- **Measuring value:** usage and time saved, shown in each client's monthly review.

## 8. Year-one income scenarios
Assumes the first client lands around months 2–4.

| | Health reports / assessments | Builds | Retainer months | Rough total |
|---|---|---|---|---|
| Slow | 3 | 1 | 6 | about $45k |
| Steady | 6 | 2 | 15 | about $90k |
| Strong | 9 | 3 | 25 | about $150k |

At 20 hours a week, Steady is realistic. Reaching Strong is the signal to go full-time.

## 9. Company setup (Texas)
Confirm the details with a CPA.
1. **Pick a name**, check it on SOSDirect, and check the domain.
2. **Form an LLC** (Form 205, which has cost $300) with a registered agent.
3. **Get an EIN** and open a business bank account.
4. **Franchise tax:** the yearly report is required even when no tax is due.
5. **⚠ Sales tax:** Texas may tax data processing and hosting services. Ask a CPA how to word the monthly retainer.
6. **Insurance:** E&O plus cyber.
7. **Basics:** bookkeeping, an email address on your own domain, and a simple website with the demo and a booking link.

## 10. Name ideas
Check availability before getting attached to one: **Plainview Data**, **Groundwork Data Co.**, **Bedrock Operations**, **Single Source Partners**, **Keel Analytics**, **Clearline**.

## 11. Open questions
1. Business name.
2. The niche to aim marketing at; decide after the first 15–20 conversations.
3. Year-one target (pick a scenario).
4. Final prices; test them in the first conversations.
