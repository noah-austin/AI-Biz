"""AI agents that work for the business, like staff members, each with a role and several jobs.

Every job runs on a schedule (or on demand from the Agents page), uses Claude through the API,
and leaves its work in the hub's Inbox for Noah to approve. Agents never send, post or
delete anything themselves, use only public web information, and stay under a monthly cap.

    python -m kit.agents tick                     # from cron every 15 minutes: run whatever is due
    python -m kit.agents run bizdev find_prospects
"""
