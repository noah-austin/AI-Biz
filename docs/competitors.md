# Snowflake and Databricks: what they are and what we learn

*Researched 2026-10-19. Figures come from third-party pricing guides and vary by source; check the vendors' own pages before quoting any.*

## What they are
- **Snowflake** sells itself as the "AI Data Cloud": a cloud data warehouse where a company stores and queries all its data, now with built-in AI (Cortex, Snowflake Intelligence). Pricing is pay-as-you-go: compute "credits" (about $2–4 each depending on edition) plus storage (about $23–40 per TB a month).
- **Databricks** sells itself as the "Data Intelligence Platform", a "lakehouse" for data engineering, analytics and AI, plus agent-building tools (Agent Bricks) and a managed Postgres (Lakebase). Also pay-as-you-go, billed per second in its own units (DBUs).

Both are **platforms, not services**. They provide the engine; somebody still has to connect the systems, define the numbers, build the reports and tools, and run it. Larger companies hire data engineers or a certified consulting partner to do that.

## How we relate to them
| | Snowflake / Databricks | Sanford Operations |
|---|---|---|
| What it is | Software platform | A service that builds and runs the whole thing |
| Who it fits | Companies with a data team, or budget for a partner | 20–1,000 people, several systems, no data team |
| Pricing | Pay-as-you-go, can surprise | Fixed quote for the build, monthly Run & Grow, hosting at cost |
| Who does the work | Your team or a partner | Us |
| Where AI fits | Tools to build AI on your data | We build the AI and agents for you |

They're not competitors for our buyers. They're the kind of platform our buyers would need a data team to use. Our kit does the same job at our clients' scale on PostgreSQL, which is cheap, standard and portable.

## What to learn from them
1. **Both rebranded around AI.** "AI Data Cloud", "Data Intelligence": the message is that AI is only as good as the data under it. That's our story too, and buyers have heard it from the big names, so it's easier to say.
2. **Both push agents now.** Agent Bricks and Snowflake Intelligence ("talk to your data") confirm that AI agents on company data are where the market is heading. Our agents are a core part, not an add-on.
3. **Their pricing scares smaller companies.** Consumption billing with surprise bills is a common complaint. Our fixed quote is a real selling point; say it plainly.
4. **Their partner world is crowded and enterprise-focused.** Hundreds of consulting firms sell Snowflake and Databricks projects to big companies. We stay in our lane: smaller companies, the whole job, plain English.
5. **"Your data, your choice" matters.** Both stress open formats and no lock-in. Our version, "you own everything, on your server or ours", answers the same worry.

## If a prospect asks
- **"Should we just buy Snowflake (or Databricks)?"** "They're excellent engines, but they need a data team to run them, and the bill depends on usage. We build the whole thing for you, at a fixed price, on a standard database you own. If you ever outgrow it, everything moves to Snowflake or Databricks cleanly."
- **"We already have Snowflake."** Good: we connect to it as a source and build the reports, tools and agents on top. (The kit would need a Snowflake connector; quote that work.)
- **"Is your database big enough?"** PostgreSQL handles hundreds of millions of rows on one server, far more than a 1,000-person company's CRM and accounting data.

## Later options
- Add Snowflake and Databricks as **sources** in the kit, for clients who already use them.
- If larger clients come, consider joining one partner program. Not now: it's built for firms selling big platform projects.

## Sources
- [Snowflake pricing options](https://www.snowflake.com/en/pricing-options/)
- [Revefi: Snowflake pricing guide](https://www.revefi.com/blog/snowflake-pricing-guide)
- [Coefficient: Snowflake Intelligence cost](https://coefficient.io/snowflake/snowflake-intelligence-cost)
- [Sacra: Databricks](https://sacra.com/c/databricks)
- [SkillScouter: Databricks review 2026](https://skillscouter.com/databricks-review/)
- [Polestar: Databricks Data + AI Summit 2026 highlights](https://www.polestaranalytics.com/blog/databricks-data-ai-summit-2026-highlights)
- [STX Next: choosing Snowflake partners](https://www.stxnext.com/blog/top-snowflake-implementation-partners)
- [MotherDuck: Snowflake alternatives 2026](https://motherduck.com/learn/top-snowflake-alternatives-2026/) (a competing vendor)
