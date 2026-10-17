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

## Open questions
- Business name (ideas in `concept.md` §8).
- Year-one income goal (scenarios in `concept.md` §5).
- Confirm the six-layer model and the three-step offer (`concept.md`).
- Where to host the public demo (a cheap VPS, or Railway).
- Texas sales tax treatment of the retainer: ask a CPA.
