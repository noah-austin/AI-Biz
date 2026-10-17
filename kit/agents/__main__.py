import argparse
import sys

from ..ai import usage
from . import engine
from .registry import BY_KEY


def main():
    p = argparse.ArgumentParser(description="Run the hub's agents.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("tick", help="run every job that's due (from cron, every 15 minutes)")
    r = sub.add_parser("run", help="run one job now")
    r.add_argument("agent", choices=sorted(BY_KEY))
    r.add_argument("job")
    sub.add_parser("list")
    a = p.parse_args()
    if a.cmd == "list":
        for agent in BY_KEY.values():
            for j in agent.jobs:
                print(f"{agent.key:8} {j.key:16} {','.join(j.days) or 'on demand':16} {j.time}  {j.name}")
        return 0
    if not usage.is_configured("agents"):
        print("No API key for the agents yet (ANTHROPIC_API_KEY_AGENTS); nothing run.")
        return 0
    jobs = engine.due_jobs() if a.cmd == "tick" else [(a.agent, a.job)]
    for agent_key, job_key in jobs:
        run_id = engine.run(agent_key, job_key)
        print(f"ran {agent_key}/{job_key} (run {run_id})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
