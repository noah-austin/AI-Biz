"""Write a demo company's systems to disk, as the files its demo connectors read."""
import argparse
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo


def main(generate, client_dir: Path, description: str):
    """generate(as_of) -> {relative path: rows}. Writes them under client_dir/source plus meta.json."""
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--as-of", default=dt.datetime.now(ZoneInfo("America/Chicago")).date().isoformat())
    p.add_argument("--out", default=str(client_dir / "source"))
    args = p.parse_args()
    as_of, out = dt.date.fromisoformat(args.as_of), Path(args.out)
    for rel, rows in generate(as_of).items():
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rows, indent=0, default=str))
        print(f"{rel:36} {len(rows):7} records")
    (out / "meta.json").write_text(json.dumps({"as_of": as_of.isoformat()}))
