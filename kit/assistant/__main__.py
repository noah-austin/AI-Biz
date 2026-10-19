"""bin/hub: the assistant's command line for the hub. See kit/assistant/__init__.py."""
import argparse
import json
import sys

from . import ALL_TOOLS, CHANGE_NAMES, ToolError, current_run_id, run


def main():
    p = argparse.ArgumentParser(prog="bin/hub", description="Work on the hub: read, propose, and (when asked) change.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("tools", help="list the tools and their inputs")
    c = sub.add_parser("call", help="run one tool; JSON input as an argument or on stdin")
    c.add_argument("name")
    c.add_argument("input", nargs="?")
    j = sub.add_parser("job", help="print the full brief for a scheduled job")
    j.add_argument("agent")
    j.add_argument("job")
    a = p.parse_args()

    if a.cmd == "tools":
        for t in ALL_TOOLS:
            kind = "CHANGE" if t["name"] in CHANGE_NAMES else ("propose" if t["name"].startswith(("propose_", "write_")) else "read")
            props = t["input_schema"]["properties"]
            req = set(t["input_schema"].get("required", []))
            fields = ", ".join(f"{k}{'*' if k in req else ''}" + (f" ({'|'.join(v['enum'])})" if v.get("enum") else "")
                               for k, v in props.items())
            print(f"{t['name']} [{kind}]: {t['description']}\n    input: {fields or '(none)'}")
        print("\n* = required. CHANGE tools alter records: confirm with Noah first.")
        return 0
    if a.cmd == "job":
        from ..agents import engine
        from ..agents.registry import BY_KEY
        if a.agent not in BY_KEY or a.job not in {x.key for x in BY_KEY[a.agent].jobs}:
            print(f"No job {a.agent}/{a.job}. Jobs: " + ", ".join(f"{k}/{x.key}" for k, ag in BY_KEY.items() for x in ag.jobs))
            return 2
        system, task = engine.brief(a.agent, a.job)
        print(f"{system}\n\n{task}")
        return 0

    raw = a.input if a.input is not None else ("" if sys.stdin.isatty() else sys.stdin.read())
    try:
        args = json.loads(raw) if raw.strip() else {}
        if not isinstance(args, dict):
            raise ValueError
    except ValueError:
        print(json.dumps({"error": "The input must be a JSON object, e.g. '{\"name\": \"Acme\"}'."}))
        return 2
    run_id = current_run_id()
    if run_id is not None and a.name in CHANGE_NAMES:
        print(json.dumps({"error": "Scheduled runs can only read and propose; changes need Noah."}))
        return 2
    try:
        print(run(a.name, args, run_id=run_id))
    except ToolError as e:
        print(json.dumps({"error": str(e)}))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
