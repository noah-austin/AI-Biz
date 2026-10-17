# The concept, v1

*Draft 2026-10-17. A working document: change it as we learn from real prospects.*

## 1. The one-sentence version

**We give mid-size companies one trusted place for their numbers, the tools to run the business on them, and AI that can answer questions and flag what matters. It's built in weeks, not months, and owned by the client.**

The original idea had three layers: data, then tools, then AI. That's sound. But the reference case showed that the parts that made it *work* sat between those layers: the agreed definitions, the data clean-up, the safety work, and the weekly back-and-forth with the owner. Those need to be part of the offer by name, or they become unpaid work.

## 2. The refined model: six layers

| # | Layer | What the client gets | Why it matters |
|---|---|---|---|
| 1 | **Connect** | Their systems (CRM, accounting, HR, projects, spreadsheets) copied hourly into one database they own. Change history kept, even where the source system drops it. | The foundation: without it, every report is a copy-paste job. |
| 2 | **Define** | The **Business Rulebook**: one written definition of every number (what "a win" is, what counts as revenue, which branches roll up where). | This was the most valuable deliverable last time. It ends the "whose number is right?" arguments. |
| 3 | **Clean** | A **clean-up list**: bad dates, duplicates, missing fields, each linked to the record so their staff can fix it at the source. | Every other tool gets more accurate. It's also a quick early win that shows value in week 2. |
| 4 | **Use** | Dashboards, reports, a planning tool that replaces their key spreadsheet, scheduled email/Teams reports, and alerts ("a $500k deal slipped a quarter"). | This is what people use every day. Every number clicks through to the records behind it. |
| 5 | **Ask** | AI on top: an "Ask" chat about their own data, a short daily list of AI insights, a drafted monthly business review, and document drafting (proposals, summaries). | The "wow" layer. It only works because layers 1–3 are solid. |
| 6 | **Run** | Monitoring, backups tested off-site, fixes, new tools each month, a monthly review with leadership. | This is the retainer. It's what keeps the system trusted, and it's the recurring revenue. |

Underneath all six: **safety** (backups, logins, read-only access for AI, secrets handled properly) and **permissions** (who sees which data).

### What's new compared with the handoff

1. **An "AI-ready data" gateway (MCP).** By 2026 every company is buying AI tools (Microsoft Copilot, ChatGPT, Claude). None of them can safely see the company's real numbers. Our database can expose a secure, read-only connection (an MCP server) so that *any* AI tool the client uses reads from the same governed source, with the Rulebook built in. This is a strong pitch: "Make your data safe and ready for whatever AI you adopt." It also means we're not competing with Copilot; we make it useful.
2. **Operating rhythm, not just dashboards.** You're a COO, and that's the difference between you and a tech shop. Package an **auto-filled weekly scorecard** and an **AI-drafted monthly business review**. Many mid-size companies run EOS (Traction), Scaling Up or similar systems with a weekly scorecard that someone fills in by hand every Monday. Automating it is a concrete, easy-to-understand pitch.
3. **Routines and alerts as a first-class tool.** Scheduled reports landing in inboxes and Teams, and threshold alerts. Many users never open a dashboard but will read an email.
4. **Per-user logins (SSO) and role permissions from day one.** The shared password was a gap last time. Mid-size companies are mostly Microsoft shops, so we use Entra ID (Microsoft 365) sign-in.
5. **Off-site backups and a tested restore** as standard. That was a gap last time too.
6. **No writing back to source systems at first.** We stay read-only on their CRM and accounting. Writing back (for example, updating a CRM field from our tool) comes later, per client, with sign-off. This keeps the risk and the liability low.

## 3. Is it sound? Honest check

**Why it works:**
- **The market gap is real.** Companies of 50–1,000 people have data spread across 4–10 systems and no data team. Big consultancies are too expensive. Off-the-shelf BI (Power BI, Tableau) needs someone in-house to build and maintain it, and they don't have that person. They end up with an analyst copying exports into Excel.
- **Your speed and cost are unusual.** About 9 days to a working system and $6 a month to run, where an agency quotes months and six figures. AI-assisted building is the edge; it's real, and it's new.
- **Your background sells it.** A COO talking to a COO or CFO about running the business beats an engineer talking about data pipelines.

**Risks, and how we handle them:**

| Risk | How we handle it |
|---|---|
| **No warm network.** The biggest risk. | Referral partners, a live demo, content from your own case, and a cheap paid first step. See section 5. |
| **20 hours a week limits capacity.** Custom builds eat time. | Build a **reusable kit** (see section 4) so each new client is about 70% setup and 30% custom. Realistically: one build at a time, plus 2–4 clients on retainer. |
| **"What if you get hit by a bus?"** Clients worry about one-person vendors. | Turn it into a selling point. They own the server, the code and the docs. It's a standard, simple stack, written up so any developer (or AI agent) can take over. |
| **Their IT department pushes back.** | Deploy into *their* cloud (Azure or AWS) under their accounts, with a written security summary. Have a short security questionnaire answer sheet ready. |
| **Liability with client data.** | A Texas LLC, professional (E&O) and cyber insurance, a proper contract (MSA + statement of work + data protection terms). AI only ever reads, never writes, and nothing is sent automatically. |
| **Bad source data makes us look wrong.** | Reproduce their existing reports to the cent first, and show the gaps as source-system fixes (the clean-up list), not our errors. |
| **Big vendors add AI to CRMs** (Salesforce Agentforce, HubSpot Breeze). | Those only see one system. Our value is *across* systems: CRM + accounting + projects, with their own rules. |
| **Too broad ("any mid-size company").** | Fine to start, but sell one **starting package** (CRM + accounting). After 2–3 clients, pick the industry that responds best and lean in. |

## 4. The reusable kit (what we build in this repo)

This is how one person scales. It's the main technical work before client one.

- **Connector library:** sync scripts for the most common systems, each with the prune safety limit and history capture. First priority: **Salesforce, HubSpot, QuickBooks Online, Excel/SharePoint files**. Then: NetSuite, Sage Intacct, Microsoft Dynamics, ADP/Paylocity, Procore.
- **Hub shell:** login (SSO), shared design, health page, usage tracking, admin page.
- **Standard tools:** the scorecard, a KPI dashboard, a drill-down table, a clean-up list, scheduled reports and alerts. All configurable per client.
- **AI layer:** the Ask chat, insights, the MCP gateway, and one key plus a cost cap and usage log per feature.
- **Ops scripts:** server setup, backups (off-site), restore test, deploy and rollback.
- **Templates:** Rulebook template, discovery questionnaire, security summary, handover pack.
- **A demo company:** a fictional mid-size business with realistic fake data, running the whole kit. This is your #1 sales tool: prospects see it working with real-looking numbers, live on a call.

**Ownership split for contracts:** the kit is your intellectual property, licensed to each client forever for their own use. Their data, Rulebook and client-specific tools belong to them. This lets you reuse the kit without ever reusing a client's work.

## 5. The offer and pricing (starting guesses to test)

| Step | What it is | Length | Price (to test) |
|---|---|---|---|
| **1. Data Health Check** | Map their systems, collect their key reports, connect read-only, deliver a data-quality report and a roadmap with their top 3 opportunities. | 2 weeks | $3,500–$5,000, credited toward step 2 |
| **2. Foundation Build** | Layers 1–5: connect 2–3 systems, the Rulebook, reproduce their reports, the scorecard plus 1–2 tools, Ask AI. | 4–6 weeks | $15,000–$30,000 |
| **3. Run & Grow** | Layer 6: monitoring, backups, fixes, new tools each month, a monthly review. | Monthly | $1,500–$4,000 / month |

Software and AI costs (server, AI usage) are paid by the client directly in their own accounts. You don't carry them or mark them up. That keeps billing simple and transparent.

**Why a paid first step:** with no network, the hardest thing is getting a "yes". $4k is an easy approval for a COO, it pays you for discovery, and it almost always turns into the build because they've seen their own messy data.

**Year-one income: three scenarios** (starting from zero, with the first client around months 2–4):

| | Health Checks | Builds | Retainer months | Rough total |
|---|---|---|---|---|
| Slow | 2 | 1 | 6 | about $40k |
| Steady | 4 | 2 | 15 | about $85k |
| Strong | 6 | 3 | 25 | about $140k |

At 20 hours a week, "Steady" is a realistic goal. If you reach "Strong", that's the signal to go full-time.

## 6. Getting clients with no network

In order of likely payoff:

1. **Referral partners.** These people already have your buyers' trust and see the pain first-hand:
   - fractional CFOs and COOs;
   - small accounting/CPA firms;
   - IT providers (MSPs);
   - Salesforce and HubSpot implementation consultants.

   They're the fastest path when you don't have a network. Offer them a referral fee (for example 10% of the first-year fees).
2. **The demo plus a case story.** "I built this for a commercial contractor in 9 days, and it runs for $6 a month." You can name the company; keep their figures out. Pair the story with the live demo company.
3. **LinkedIn as an operator, not a vendor.** Short posts from a COO's point of view: the 2111 close-date story, "never average percentages", "your CRM's AI only sees your CRM". It builds credibility over time.
4. **Local groups.** In Texas: Vistage and EO chapters, chambers of commerce, industry associations. A 20-minute talk, "What AI can actually do with your company's data", with the live demo.
5. **Direct outreach** to COOs and CFOs at 50–500-person companies, with a specific hook: "I'll show you your Monday scorecard filling itself in."

## 7. Company setup (Texas)

Confirm the details with a CPA. These are the usual steps:

1. **Pick a name.** Check it on the Texas Secretary of State site (SOSDirect) and check the domain is free.
2. **Form an LLC** (Form 205 with the Texas SOS; the filing fee has been $300) and name a registered agent (you, or a service).
3. **Get an EIN** from the IRS (free, online) and open a **business bank account**.
4. **Texas franchise tax:** you file a yearly report. Below the revenue threshold (about $2.47M) no tax is due, but **the report itself is still required**.
5. **⚠ Texas sales tax:** Texas taxes "data processing services" (generally on 80% of the charge), and hosting and running data systems can fall under it. Consulting and custom software work are treated differently. **Ask a CPA how to split your invoices.** This could affect how we word the Run & Grow retainer.
6. **Insurance:** professional liability (E&O) plus cyber. Some clients will require it in the contract.
7. **Contracts:** a master services agreement, a statement of work template, and data protection terms. A lawyer reviews them once; then you reuse them.
8. **Basics:** bookkeeping (QuickBooks or Wave), a business email on your domain, a simple website with the demo and a booking link.

## 8. Name ideas

Short, credible, not too "techy". Check availability before falling for one.

- **Plainview Data**: your business, in plain view (Plainview is also a Texas town)
- **Groundwork Data Co.**: the foundation everything else stands on
- **Bedrock Operations**
- **Single Source Partners**
- **Keel Analytics**: keeps the business steady
- **Clearline**
- **Northgate Data**
- **Ledger & Lantern**

## 9. Decisions needed from Noah

1. Do the six layers and the three-step offer feel right?
2. A name, or any you like or dislike from the list.
3. Year-one income goal (pick a scenario).
4. What to build first in this repo: **the demo company plus kit** (recommended), or sales material first.
