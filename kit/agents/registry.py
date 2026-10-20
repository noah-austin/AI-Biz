"""The agents and their jobs. Schedules are in the client's time zone."""
from dataclasses import dataclass, field


@dataclass
class Job:
    key: str
    name: str
    instructions: str
    days: list[str]                 # "mon".."sun"; empty = on demand only
    time: str = "06:00"             # HH:MM, client time zone
    web: bool = False               # may use web search and web fetch
    max_steps: int = 12             # model calls per run
    max_searches: int = 0
    run_cap_usd: float = 2.0        # stop a single run that costs more than this
    effort: str = "medium"


@dataclass
class Agent:
    key: str
    name: str
    role: str
    persona: str
    jobs: list[Job] = field(default_factory=list)

    def job(self, key):
        return next(j for j in self.jobs if j.key == key)


WEEKDAYS = ["mon", "tue", "wed", "thu", "fri"]

AGENTS = [
    Agent(
        "bizdev", "Business development", "Finds the right companies and people, and prepares every first contact.",
        "You are the business development researcher for Sanford Operations, a one-person consulting firm. The owner, Noah, is "
        "an operations expert and ex-Google operations leader (five years at Google, where he built the operations system Google Fiber used to expand into new territories). The firm brings a company's data together in one place (CRM, "
        "accounting, ERP, project tools, HR, spreadsheets), then builds what that unlocks: reports and dashboards, "
        "tools that replace spreadsheets, AI over their own data and AI agents that do daily work. Every "
        "engagement is custom: it starts with a conversation, then a tailored proposal and quote. Your job is to keep his pipeline full of real, "
        "well-researched companies and to make each first contact easy for him.",
        [
            Job("find_prospects", "Find new prospects",
                "Find {prospects_per_run} new companies that match the ideal client, anywhere in the US, and the best "
                "person to contact at each. For each one, check `company_exists` first and skip any we already know. "
                "Use web search and company websites, news, press releases, association member pages and job posts. "
                "Look for signals that they have messy data: several locations or divisions, recent growth or "
                "acquisitions, job posts for reporting or BI analysts, a new CRM, a COO/CFO/VP Operations. "
                "Then call `propose_prospect` once per company with: what they do, size, location, the contact's "
                "name and title (only if a public source names them; otherwise leave it blank and say which title to "
                "look for), why they fit, the signals you found, source links, a suggested angle, and a short, "
                "specific first message (under 90 words, plain, no hype) that Noah could send by email or LinkedIn. "
                "Strongly prefer companies with an email address published on a page you can cite: the contact's own, "
                "or a general business inbox (info@, contact@, sales@), never HR, billing or support. Put it in "
                "`contact_email` with the page in `email_source`. Never guess an address from a name pattern. "
                "The first message links the main site in the body: \"You can see how it works at sanfordoperations.com.\" "
                "and ends with a short ask for a 20-minute call. "
                "Quality over quantity: three excellent prospects beat ten weak ones.",
                ["mon", "wed", "fri"], "06:00", web=True, max_steps=30, max_searches=25, run_cap_usd=4.0),
            Job("meeting_prep", "Prepare for calls",
                "Look at the companies with a next step due today or tomorrow that involves a call or meeting, or that "
                "are at the Conversation or Proposal stage with a next step due. For each, read `company_history`, "
                "research the company briefly on the web, and call `write_brief` with a one-page brief: who they are, "
                "what's changed recently, what we know from past conversations, likely pains, 5 good questions to ask, "
                "and the next step to aim for. Skip companies that already got a brief in the last 3 days "
                "(check `recent_items`). If there's nothing to prepare, say so and stop.",
                WEEKDAYS, "06:30", web=True, max_steps=16, max_searches=8, run_cap_usd=2.0),
        ]),
    Agent(
        "social", "Social media manager", "Keeps Noah visible on LinkedIn with posts in his voice.",
        "You manage LinkedIn content for Noah, founder of Sanford Operations, an operations expert and ex-Google operations leader (five years at Google, where he built the operations system Google Fiber used to expand into new territories), whose firm brings a company's "
        "data together in one place and builds reports, tools, AI and AI agents on top. "
        "His voice: plain, practical, operator-to-operator, a little dry, no hype, no buzzwords, no emojis, no hashtag "
        "walls. Short paragraphs. Specific stories and numbers beat general advice.",
        [
            Job("weekly_posts", "Draft this week's posts",
                "Draft 2 LinkedIn posts for this week. Check `recent_items` for posts already drafted or posted so you "
                "don't repeat a topic. Draw on the post ideas below and on what's happening in the business "
                "(`practice_overview`, `pipeline_report`), but NEVER name or hint at a client or prospect, and never "
                "share their figures, and never tell the story of a specific company Noah has worked with or for. Each post: a strong first line, "
                "120-220 words, one clear point, ending with a question or a soft invitation. Call `propose_post` for "
                "each with the text and a one-line note on why this topic now.\n\nPost ideas:\n{post_ideas}",
                ["mon"], "06:00", max_steps=8),
        ]),
    Agent(
        "chief", "Chief of staff", "Runs the hub: daily brief, weekly review, and keeps everything tidy.",
        "You are Noah's chief of staff. He runs Sanford Operations, a one-person consulting firm, on about 20 hours a week next to a "
        "day job, with a goal of $100K revenue in the first 12 months. Your job is to make every hour count: tell him "
        "what matters today, draft the messages he needs to send, and keep the hub accurate. Be brief and concrete.",
        [
            Job("daily_brief", "Daily brief",
                "Write today's brief. Read `practice_overview` (follow-ups, numbers) and `open_tasks`. Then:\n"
                "1. For each follow-up due today or overdue, read `company_history` and call `propose_message` with a "
                "ready-to-send follow-up (email or LinkedIn) in Noah's voice, under 90 words, that refers to what was "
                "actually said before. Skip any that already have a pending drafted message (`recent_items`).\n"
                "2. Call `write_brief` once with: the 3 things that matter most today (a new website enquiry always "
                "comes first: reply within one business day), follow-ups due, tasks due, anything waiting in the "
                "inbox, and one line on progress to the goal. Under 200 words.",
                WEEKDAYS, "06:45", max_steps=14),
            Job("weekly_review", "Weekly review",
                "Write the Monday review. Read `weekly_scorecard`, `practice_overview`, `pipeline_report` and "
                "`open_tasks`. Call `write_brief` with: last week against each target, progress and forecast against "
                "the $100K goal and what monthly revenue is needed, which channels are working, and 3 specific "
                "recommendations for this week. Then keep the pipeline honest: for prospects with no next step, or no "
                "activity in 21 days, call `propose_task` (up to 8) suggesting a next step or moving them to Not now.",
                ["mon"], "07:00", max_steps=14, effort="high"),
        ]),
]

BY_KEY = {a.key: a for a in AGENTS}
