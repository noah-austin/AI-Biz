# The concept, v3

*2026-10-17. Replaces v2 (still in git history). A working document: change it as real conversations teach us.*

## 1. What the business is

**We bring a company's data together in one place, then build what that unlocks: reports that build themselves, tools that replace spreadsheets, and AI and AI agents that do real work.**

We add to what a company already has. We don't replace their systems, and we don't sell "fixing" their data. Buyers don't wake up wanting "data consolidation"; they want:
- a Monday meeting where nobody argues about whose number is right;
- reports that build themselves instead of eating someone's week;
- to know early when a big deal slips or a customer stops paying;
- AI that gives real answers about *their* business, and agents that take work off their team.

## 2. How it works: platform, method, custom plan

Like a good Salesforce consultant, we bring three things:

| | What it is | Why it matters |
|---|---|---|
| **A platform** | The kit (`kit/`): sync from their systems, one database they own, business rules, a web hub, an AI layer, agents. | We don't start from zero, so builds are faster and cost less. |
| **A method** | Understand the business → write the rulebook → connect the data → reproduce their existing reports to the cent → build what they need most → keep it trusted. | Reliable results, and numbers people trust because they've seen them match. |
| **A custom plan** | Which systems, which numbers, which tools, AI and agents matter most to *this* client. | Every company is different. The plan is tailored; the platform and method stay the same. |

## 3. What we build

All of it sits on the same foundation, and each client gets the mix that fits them:
- **The foundation:** every system with data in it (CRM, accounting, ERP, project and field-service tools, HR, spreadsheets, databases) connected into one database, with every number defined once in a plain-English rulebook.
- **Reports and dashboards:** a self-filling weekly scorecard, the monthly review, drill-downs to every record, location- and role-level access.
- **Tools:** simple apps that replace the spreadsheets a company runs on (forecasts, trackers, workbooks).
- **Push, not pull:** scheduled reports and alerts by email or Teams.
- **AI:** an "Ask AI" assistant over their own data, insights, and a secure read-only link so Copilot, ChatGPT or Claude can use the same data.
- **AI agents (a core part):** assistants with a job, working from the data every day: daily briefs, drafted reports, meeting prep, follow-up watch, research. Agents prepare the work; a person approves anything that goes out. Our own hub is the working example.
- **Side benefit, never the headline:** the kit flags records that look wrong in their systems. Mention it in passing at most.

### What we don't do
- implementing or replacing ERPs and CRMs (we work alongside their consultant);
- AI that isn't connected to their data;
- training custom AI models;
- writing back into their systems without explicit sign-off.

### Where it runs (client's choice)
- **On their own server**, in their name; we manage it. They own everything and can take it over.
- **Hosted by us.** Each hosted client gets its own separate server in our account; client data never shares a server with ours or another client's. Hosting is billed through to them.

Either way the data is theirs, it's fully documented, and there are no per-seat licences.

## 4. How clients buy

1. **A conversation** (one or two calls, free): how they run, which systems hold their data, what they want to see and do.
2. **A custom proposal** (free): the plan, what we build first, and a fixed quote. Priced to their setup: how many systems, how much data (records and fields), and what we build on top.
3. **The build:** length depends on scope and is never advertised.
4. **Run & Grow** (monthly): monitoring, backups, fixes, new tools, new agents and AI uses, and a monthly review with leadership.

No prices or timelines are published. Internal planning guesses only: a build around $15,000–30,000 and Run & Grow around $1,500–4,000 a month. Replace these with real quotes as they happen. Server and AI usage are billed to the client at cost.

**Founding-client deal (first 1–2 clients):** a discount, in exchange for a case study and a reference.

## 5. Why this beats being a general AI consultant
- **General AI consulting is crowded and vague.** In 2026 everyone is an "AI consultant", and the work tends to be workshops, decks and one-off automations.
- **AI only works when it can see the company's data.** We build that foundation first, so our AI and agents actually work. A general consultant's agents can't see across systems; ours can.
- **The foundation brings recurring revenue.** Once leadership runs on it and agents do daily work on it, the monthly fee lasts for years. One-off AI projects end.
- **The market is big enough.** Hundreds of thousands of small and mid-size US companies run on several systems with no data team. We need 5–10 clients.
- **Our edge:** operators (COO / chief of staff) selling to operators. A tech shop can't sell "your company runs on one set of numbers" with the same credibility.

## 6. Who we sell to
- **Buyer:** COO, CFO, owner or president of a small or mid-size company, **any industry, anywhere in the US**, that runs on several systems and has no data team.
- **Pain signals:** leadership numbers built by hand in Excel; reports that don't match; data in many systems; a new system nobody trusts; "we bought Copilot and it can't answer anything".
- **Marketing focus:** any industry on the website. Watch which industries respond best in the first 15–20 conversations; if one stands out, lean examples and outreach toward it.

## 7. Getting the first clients (no warm network)
1. **15–20 conversations in the next month** with COOs, CFOs and owners. Ask what's painful, what they've tried, and what it's worth to them. These calls are market research and pipeline at the same time.
2. **Referral partners:** fractional CFOs and COOs, CPA firms, IT providers, and CRM/ERP consultants. Referral fee of about 10% of first-year fees.
3. **The live demo** (the fictional Bluestem company). The first reference company is never named or described on the website; stories in conversation stay anonymous and figure-free.
4. **LinkedIn as an operator, not a vendor:** short posts about running a company on its data, what agents can actually do, and "your CRM's AI only sees your CRM".
5. **Local groups:** Vistage and EO chapters, chambers of commerce, trade associations. A 20-minute talk: "What AI can actually do with your company's data."
6. **The AI-readiness angle:** "Before you roll out Copilot or agents, put your data in one place."
7. **Our own agents do the legwork:** the business development agent finds and researches prospects every Mon/Wed/Fri; Noah makes the contact.

## 8. Risks to watch
- **"Any industry" is hard to market with no network.** Referral partners and the demo carry most of the load early; revisit after 20 conversations.
- **Hosting client data raises the stakes:** insurance (E&O plus cyber), the security one-pager and the contracts must be in place before the first hosted client.
- **Custom quotes take time to write.** Build a proposal template from the first one so the next takes an hour, not a day.
- **20 hours a week:** one build at a time until there's help or more hours.

## 9. Building the business, not just the software

**Stop adding features until a client needs them.** The demo is good enough to sell. The first client decides the next connector and the next tool. In the next 60 days, about 70% of the time goes to selling.

**Must-haves before client #1:**
- [x] Google sign-in (Microsoft for clients on Microsoft 365: later)
- [x] Alerts when a sync, backup or agent job fails
- [x] A one-command installer, so every client runs the same kit
- [ ] Contracts: master services agreement, statement of work, data terms (including that data goes to Anthropic's API, which doesn't train on it)
- [ ] One-page security summary, plus standard answers to IT questionnaires
- [ ] Insurance: professional liability (E&O) plus cyber
- [ ] The connector client #1 actually needs
- [ ] A hosted-client setup: one separate server per hosted client, in our account (client data never shares a server with ours or another client's)

**To scale on 20 hours a week (soon after):**
- **One product, many installs.** Clients only differ by settings and their own small client folder; updates go to everyone.
- **Agents as a product:** turn the agent engine from our own hub into a standard part of every client install (daily briefs, drafted reports, meeting prep, follow-up watch).
- **A dashboard for Noah** showing the health of every client install on one screen.
- **Open-source connectors (dlt)** for the long tail of systems, plus a spreadsheet upload for quick wins.
- **Measuring value:** usage and time saved, shown in each client's monthly review.

## 10. Year-one income scenarios
Assumes the first client lands around months 2–4, an average build of about $20k and an average retainer of about $2,500 a month (our planning guesses, to replace with real quotes).

| | Builds | Retainer months | Rough total |
|---|---|---|---|
| Slow | 1 | 6 | about $35k |
| Steady | 3 | 15 | about $100k |
| Strong | 5 | 25 | about $160k |

At 20 hours a week, Steady is realistic. Reaching Strong is the signal to go full-time.

## 11. Company setup (Texas)
Confirm the details with a CPA.
1. **Pick a name**, check it on SOSDirect, and check the domain.
2. **Form an LLC** (Form 205, which has cost $300) with a registered agent.
3. **Get an EIN** and open a business bank account.
4. **Franchise tax:** the yearly report is required even when no tax is due.
5. **⚠ Sales tax:** Texas may tax data processing and hosting services. Ask a CPA how to word the monthly retainer.
6. **Insurance:** E&O plus cyber.
7. **Basics:** bookkeeping, an email address on your own domain (Google Workspace), and the website (built; see `website/`).

## 12. Name ideas (shortlist with screening in `docs/names.md`)
Check availability before getting attached to one: **Plainview Data**, **Groundwork Data Co.**, **Bedrock Operations**, **Single Source Partners**, **Keel Analytics**, **Clearline**.

## 13. Open questions
1. Business name.
2. Whether to lean toward an industry, after the first 15–20 conversations.
3. Real prices, from the first proposals.
4. Who is "we" as it grows: subcontractors, a partner, or staying solo for year one.
