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
| Entry offer | ~~CRM Health Report~~ dropped (see "how clients start" below) | Was Claude's suggestion; it framed the business as fixing data, which it isn't. |
| Niche | Take any good fit; leading guess for marketing is contractors and field services | Decide after 15–20 conversations. |
| Focus | Stop adding features until a client needs them; ~70% of time goes to selling for 60 days | Must-haves before client #1 are listed in concept.md §9. |

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

## 2026-10-17: website
| Topic | Decision | Notes |
|---|---|---|
| Hosting | Same server as the hubs, as its own small app (`website/`) | The website's database login can only add enquiries. `www` redirects to the main address. |
| Enquiries | The contact form lands in the company hub's Inbox, with an instant phone alert | One tap adds it to the pipeline. The chief of staff puts new enquiries first in the daily brief. |
| Spam | Hidden honeypot field, minimum time on page, signed form token, 5 per visitor per hour | No captcha, so nothing annoys real visitors. |
| Demo access | The "See a live demo" button signs visitors into Bluestem as a read-only guest | No password needed. Guest questions to Ask AI share one daily limit. |
| Name | Sanford Operations (sanfordoperations.com) | Chosen 2026-10-18 from 175+ screened names (`docs/names.md`). Set in `website/config.toml` and the company hub config. |
| Prices | No prices published on the website or sales material | Every quote depends on the company: how many systems, records and fields. Prospects get a fixed quote after the first call. The ranges in `concept.md` are an internal guide only. |

## 2026-10-17: how clients start
| Topic | Decision | Notes |
|---|---|---|
| What we sell | The end product: their data in one place, with tools and AI built on top. We add to what they have; we don't sell "fixing" their data. | The kit's checks for records that look wrong are a minor side benefit. Mention in passing at most. |
| How clients start | A conversation, then a written custom proposal with a fixed quote | No packaged entry offer and no paid assessment. |
| Timelines | Never advertised | Builds depend on scope; the proposal covers timing. |

## 2026-10-17: concept v3 and website second pass
| Topic | Decision | Notes |
|---|---|---|
| Headline | "All your data in one place, and everything it unlocks." | Data in one place leads; tools, AI and agents are what it unlocks. |
| Voice | "We" (a firm) | Noah is named once, as founder, on the About page. Personal emails still come from Noah as "I". |
| Origin story | Not on the website or in posts | The first company is never named or described publicly. |
| AI agents | A core part of what clients get | Daily briefs, drafted reports, meeting prep, follow-up watch, research. A person approves anything that goes out. |
| Systems | Anything with data in it | The contact form asks "main systems you use" (free text) instead of a CRM list. |
| Hosting | Client's choice: their own server (we manage) or hosted by us | Each hosted client gets its own separate server in our account; never shared. |
| Audience | Leaders of small and mid-size companies, any industry, US-wide | Lean toward an industry only if one clearly stands out in the first 15–20 conversations. |

## 2026-10-18: name
| Topic | Decision | Notes |
|---|---|---|
| Business name | **Sanford Operations** | Domain sanfordoperations.com is available (checked by Noah). Classic firm style, as Noah chose. "Operations" says what we're about: running the company on its data. Screen: no company uses the exact name; avoid "Sanford Data/Analytics" (Sanford Health's data programme) and "Sanford & Co" (a Las Vegas accounting firm). |
| Addresses | Website sanfordoperations.com; hub hub.sanfordoperations.com; demo demo.sanfordoperations.com; email hello@sanfordoperations.com | Email via Google Workspace on the domain. |
| Still to do | Texas SOSDirect name search; USPTO search (classes 35 and 42); LLC filing as Sanford Operations LLC | Domain registered and Google Workspace set up 2026-10-18 (noah@sanfordoperations.com). |

## 2026-10-18: logo
| Topic | Decision | Notes |
|---|---|---|
| Logo | The seal: SANFORD on top, OPERATIONS below, stars at the sides, serif S centre; oxblood on parchment | No date or place on it. Files and rules in `docs/brand.md`. |
| Website look | Restyled to match the seal: parchment, oxblood and brass, Playfair Display headings | Replaces the blue and green. |
| Website refinements | Added a trust line, a "Who we work with" strip, an FAQ, and "Now taking a small number of founding clients" on the calls to action | The founding-client line matches the founding-client deal in `concept.md`; remove it once the first clients are signed. |

## 2026-10-18: demo additions
| Topic | Decision | Notes |
|---|---|---|
| Demo pages | Added Forecast, Alerts and AI agents pages to the hub (for every client, not just the demo) | The facts come from `kit/watch.py`; alert lines are set per client under `[watch]`. |
| Agents in the demo | Agent output is prepared by fixed rules from the data, and the page says so | Keeps the public demo free of AI cost and of anything that could send. "Approve and send" is switched off. |
| Payment reminders | Friendly reminder drafts only for invoices 61 to 120 days late | Older ones need a phone call from a person. |
| Forecast calls | Start from stage (75%+ Commit, 40%+ Best case); admins save changes, with who and when | Guests can try changes but nothing is saved. |

## 2026-10-18: domain
| Topic | Decision | Notes |
|---|---|---|
| Domain and email | Buy sanfordoperations.com during Google Workspace signup (registered through Squarespace) | Simplest: Google sets up the email records. Server records are added in Squarespace's DNS page. Keep the recovery email on Noah's personal Gmail. |

## 2026-10-18: tagline
| Topic | Decision | Notes |
|---|---|---|
| Tagline | "Your data in one place. Numbers everyone trusts, put to work." | Replaces "All your data in one place, and everything it unlocks", which was too vague about what clients get. Where two lines fit, the same words split after the first sentence. |

## 2026-10-18: data hub and explainer
| Topic | Decision | Notes |
|---|---|---|
| Name for the centre | "Your data hub" (was "One place"), with "every system, together" | Matches the demo's "Bluestem Hub"; a client's own becomes "[Company] Hub". |
| Explainer | 24-second animation on the home page and as an MP4 for LinkedIn. Since 2026-10-19 the site plays MP4s: a wide cut, and a tall cut for phones (the scaled CSS version was unreadable on phones and unreliable on iPhones) | Story: data split across systems → brought together → works as one → we build on it (not reconciliation). Source in `website/brand/animation/`; both cuts render to `website/static/video/`. Numbers on screen are illustrative. |

## 2026-10-19: our server
| Topic | Decision | Notes |
|---|---|---|
| Server | DigitalOcean droplet, Ubuntu 24.04, 4 GB / 2 CPUs, weekly backups | Runs the company hub, the Bluestem demo and the website. Demo and our own data only, never client data. |
| DNS | A records for `@`, `www`, `hub`, `demo` point at the droplet; DMARC added; Squarespace parking records removed | Email records (MX, SPF, DKIM) untouched. |
| Access | Browser console with a strong password (no SSH key); GitHub connected with `gh auth login` | Claude Code runs on the server under Noah's subscription, reached through Remote Control ("Biz server"). A one-repo deploy key was offered and declined for now. |
| Other videos | 3D explainer ("The foundation", 29 s) and a 60 s demo walkthrough | In `website/brand/animation3d/` and `website/brand/demo-video/`; where they go is still to decide. |
| Tour and overview videos (2026-10-20) | What we build plays a 47 s tour: its own title card, systems connected into one hub in three numbered steps, then the demo hub (home, scorecard, Ask AI, alerts, agents), played on request, with a phone cut whose camera follows the action. The 52 s overview (explainer story, then the demo) is kept for LinkedIn and follow-up emails. | The tour opens differently from the home page video so visitors don't skip it as a repeat. Source: `website/brand/demo-video/combined.py`. |
| One AI assistant | Claude Code on the server, on Noah's Claude subscription, is the one assistant: chat (Claude app, "Biz server"), hub work, prospecting and the agents' jobs on request | Works on the hub only through `bin/hub` (kit/assistant), confirms every change with Noah, and changes the ideal client by chat. Chosen over the API to avoid per-use cost. Scheduled jobs on the subscription are not built yet (needs Noah's OK); until then they need an API key. The hub's web chat stays API-based and optional. |
| Industry demos | Five fictional demo companies, picked from sanfordoperations.com/demo: facility services (Bluestem), distribution (Bramblewood), professional services (Kestrel Ridge), construction (Mesquite Ridge), manufacturing (Cottonwood) | Each is its own install at <industry>.demo.sanfordoperations.com, built on a shared demo engine (kit/demos) with stories and data problems planted. New kit modules they brought: orders and shipping, projects and time, job cost, production. More industries (healthcare, logistics, property management, multi-unit retail) only if prospects ask. |

## Open questions
- Texas sales tax treatment of the retainer and hosting: ask a CPA.
- Hosting price for hosted clients (at cost, or a set monthly fee).
