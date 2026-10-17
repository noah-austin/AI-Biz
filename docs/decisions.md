# Decisions log

## 2026-10-17: starting point
| Topic | Decision | Notes |
|---|---|---|
| Target market | Any mid-size company | No industry niche to start. The reference case was a commercial contractor. |
| Pricing model | Setup fee + monthly retainer | Fixed fee for the foundation and first tools; the retainer covers hosting upkeep, support and new tools. |
| Ownership | Client owns the infrastructure, Noah manages it | Server and accounts sit in the client's name; Noah manages them on retainer. |
| Commitment | Side project to start | Keeping the current job while landing the first 1–2 clients. |

| Reference company | Can be named; no referral | Noah is cleared to do this work and reuse what's needed. Settled; don't re-raise. Keep their figures out of everything. |
| Noah's background | Business operations (COO / chief of staff) | Sell as an operator to COOs and CFOs. |
| Network | No warm leads | Go-to-market leans on referral partners, the demo and content. |
| Location | Texas | Texas LLC. |
| Time | 20 hours a week | |

## 2026-10-17: demo and kit, first build
| Topic | Decision | Notes |
|---|---|---|
| Demo company | Bluestem Facility Services (fictional): Texas commercial facility services, 6 branches, CRM + accounting | Broadly relatable to mid-size B2B buyers. Made-up data with planted data problems. |
| Standard tables | Every connector maps into one standard set of CRM and accounting tables | Tools are written once and work for every client. |
| Chart library | Chart.js 4.4.1 bundled with the kit | No outside CDN, which locked-down client IT prefers. |
| Sign-in | Passwords per user for now, with branch-level access | Microsoft/Google sign-in is next; only `kit/hub/auth.py` changes. |

## 2026-10-17: AI layer
| Topic | Decision | Notes |
|---|---|---|
| Model | Claude Opus 5.5 for chat and insights | Set per client in `config.toml`. Chat at effort "medium", insights at "high". |
| How it reads data | Through the hub's own metric functions; read-only SQL only for all-branch users | Figures match the pages; branch limits can't be bypassed. |
| Refusals | Server-side fallback ("default") is on | If Claude declines a question, the API retries on the model Anthropic recommends. |
| Caps (demo) | Chat $50/month, insights $25/month, 40 questions per person per day | Each feature has its own API key. |
| Costs | Not measured yet | Measure on real questions once the key is in, before quoting clients. |

## 2026-10-17: positioning (concept v2)
| Topic | Decision | Notes |
|---|---|---|
| What we are | Not a general AI consultant: "we help mid-size companies run on their data" | Data consolidation is the engine; the outcome is what we sell. |
| Delivery model | Platform (the kit) + method + a custom plan per client | Like a Salesforce consultant, but we own the platform. |
| Entry offer | CRM Health Report, ~1 week, $1,500–2,500 | Built on the kit's clean-up checks. |
| Niche | Take any good fit; leading guess for marketing is contractors and field services | Decide after 15–20 conversations. |
| Focus | Stop adding features until a client needs them; ~70% of time goes to selling for 60 days | Must-haves before client #1 are listed in concept.md §7. |

## 2026-10-17: our own server
| Topic | Decision | Notes |
|---|---|---|
| Hosting | Our own VPS (DigitalOcean, 4 GB), not Railway | Full control, same setup as client installs. |
| How Claude works on it | Claude Code installed on the server, linked with Remote Control | Shows up in the Claude app; uses the subscription, not the API. Cloud sessions can't SSH, so code also flows through GitHub. |
| What runs there | Company hub, Bluestem demo, later the website | Never client data. Steps in `docs/server-setup.md`. |

## 2026-10-17: company hub
| Topic | Decision | Notes |
|---|---|---|
| Where prospect and client info lives | Built into the hub (the "practice" app), not an outside CRM | Prospects, partners, conversations, engagements, time, invoices, expenses. Exports to Excel any time. |
| One kit, different apps | `apps` setting per install | Clients and the demo get analytics; our hub gets the practice tracker. Ask AI adapts to each. |
| Invoices | Sent from an invoicing tool; recorded in the hub | The hub tracks revenue, cash and overdue invoices; it doesn't send invoices (yet). |

## 2026-10-17: goal, Google Workspace, agents
| Topic | Decision | Notes |
|---|---|---|
| Revenue goal | $100K within the first 12 months: Oct 1, 2026 – Sep 30, 2027 | Tracked on Today with pace, forecast and the monthly amount needed. |
| Email and sign-in | Google Workspace (once the name and domain exist) | Google sign-in for the hub and Gmail drafts for the agents come after Workspace is set up. |
| Agents | Three roles, each with several jobs: business development, social media manager, chief of staff | Work lands in the Inbox; nothing is sent automatically. Public web only, no LinkedIn scraping. $60/month cap to start. |
| Prospecting scope | Small and mid-size companies nationwide, any industry | The ideal-client description is in `clients/company/config.toml`. |
| Contact data | Public web only for now | Add a paid data service later if volume needs it. |

## 2026-10-17: must-haves
| Topic | Decision | Notes |
|---|---|---|
| Alerts | ntfy push notifications to Noah's phone now; email once Workspace exists | Free, no account; the topic name is kept secret like a password. |
| Installer | `ops/install.sh` sets up servers, adds installs, updates everything | Same tool for our server and client servers. |
| Sign-in | Google sign-in built; switches on once Workspace exists | Only existing hub users can sign in; optionally one domain only. |
| Business name style | Plain and credible | Shortlist with domain checks still to do. |

## Open questions
- Business name (ideas in `concept.md` §8).
- Year-one income goal (scenarios in `concept.md` §5).
- Confirm the six-layer model and the three-step offer (`concept.md`).
- Where to host the public demo (a cheap VPS, or Railway).
- Texas sales tax treatment of the retainer: ask a CPA.
