"""Copy every configured source into the database. Run hourly from cron.

    python -m kit.sync            # all sources
    python -m kit.sync --dry-run  # fetch and report, change nothing

Snapshot objects: upsert on id, stamp synced_at, then remove rows the source no
longer returns. The removal has a safety limit: it refuses if the source
returned nothing, or if it would delete more than PRUNE_MAX_FRACTION of the
table. One bad pull must never wipe a table.

History objects: only ever add rows.
"""
import argparse
import sys
import time

import psycopg2.extras

from . import db
from .config import get_settings
from .connectors import REGISTRY
from .connectors.base import ObjectSpec

PRUNE_MAX_FRACTION = 0.10
LOCK_ID = 0x5EED  # advisory lock so two syncs never overlap


class SyncRefused(RuntimeError):
    pass


def _record(conn, spec: ObjectSpec, source: str, status: str, message: str, seen=None, upserted=None, pruned=None):
    db.execute(
        """INSERT INTO core.sync_state (object, source, last_attempt_at, last_success_at, last_status,
                                        last_message, rows_seen, rows_upserted, rows_pruned)
           VALUES (%(o)s, %(s)s, now(), CASE WHEN %(ok)s THEN now() END, %(st)s, %(m)s, %(seen)s, %(up)s, %(pr)s)
           ON CONFLICT (object) DO UPDATE SET source = EXCLUDED.source, last_attempt_at = now(),
               last_success_at = CASE WHEN %(ok)s THEN now() ELSE core.sync_state.last_success_at END,
               last_status = EXCLUDED.last_status, last_message = EXCLUDED.last_message,
               rows_seen = EXCLUDED.rows_seen, rows_upserted = EXCLUDED.rows_upserted,
               rows_pruned = EXCLUDED.rows_pruned""",
        {"o": spec.name, "s": source, "ok": status in ("ok", "warning"), "st": status, "m": message,
         "seen": seen, "up": upserted, "pr": pruned},
        conn,
    )


def sync_object(conn, spec: ObjectSpec, rows: list[dict], max_prune_fraction: float = PRUNE_MAX_FRACTION):
    """Write one object's rows. Returns (upserted, pruned, warning or None)."""
    if not rows:
        raise SyncRefused(f"{spec.name}: the source returned 0 rows; refusing to touch the table.")
    ids = [r[spec.key] for r in rows]
    if len(set(ids)) != len(ids):
        raise SyncRefused(f"{spec.name}: the source returned duplicate ids.")
    cols = spec.columns
    values = [tuple(r.get(c) for c in cols) for r in rows]
    col_sql = ", ".join(cols)
    with conn.cursor() as cur:
        if spec.mode == "history":
            cur.execute(f"SELECT count(*) FROM {spec.table}")
            before = cur.fetchone()[0]
            psycopg2.extras.execute_values(
                cur,
                f"INSERT INTO {spec.table} ({col_sql}, synced_at) VALUES %s ON CONFLICT ({spec.key}) DO NOTHING",
                values, template="(" + ", ".join(["%s"] * len(cols)) + ", now())", page_size=1000)
            cur.execute(f"SELECT count(*) FROM {spec.table}")
            return cur.fetchone()[0] - before, 0, None
        updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols if c != spec.key)
        psycopg2.extras.execute_values(
            cur,
            f"INSERT INTO {spec.table} ({col_sql}, synced_at) VALUES %s "
            f"ON CONFLICT ({spec.key}) DO UPDATE SET {updates}, synced_at = now()",
            values, template="(" + ", ".join(["%s"] * len(cols)) + ", now())", page_size=1000)
        upserted = len(values)
        cur.execute("CREATE TEMP TABLE _seen (id text PRIMARY KEY) ON COMMIT DROP")
        psycopg2.extras.execute_values(cur, "INSERT INTO _seen (id) VALUES %s", [(i,) for i in ids], page_size=5000)
        cur.execute(f"SELECT count(*) FROM {spec.table}")
        total = cur.fetchone()[0]
        cur.execute(f"SELECT count(*) FROM {spec.table} t WHERE NOT EXISTS (SELECT 1 FROM _seen s WHERE s.id = t.{spec.key})")
        stale = cur.fetchone()[0]
        warning = None
        pruned = 0
        if stale and stale > max_prune_fraction * total:
            warning = (f"Source no longer returns {stale} of {total} rows; that's over "
                       f"{max_prune_fraction:.0%}, so nothing was removed. Check the source before pruning.")
        elif stale:
            cur.execute(f"DELETE FROM {spec.table} t WHERE NOT EXISTS (SELECT 1 FROM _seen s WHERE s.id = t.{spec.key})")
            pruned = cur.rowcount
        cur.execute("DROP TABLE IF EXISTS _seen")
        return upserted, pruned, warning


def load_reference(conn, client: dict):
    """Copy the business settings from config.toml into the database."""
    db.execute("INSERT INTO core.settings (key, value) VALUES ('timezone', %(tz)s) "
               "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
               {"tz": client.get("timezone", "America/Chicago")}, conn)
    people = client.get("people", {})
    for key, default in (("frontline_department", "Field Service"), ("license", "")):
        db.execute("INSERT INTO core.settings (key, value) VALUES (%(k)s, %(v)s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                   {"k": key, "v": people.get(key, default)}, conn)
    for b in client.get("branches", []):
        db.execute("""INSERT INTO core.branches (code, name, region, active) VALUES (%(code)s, %(name)s, %(region)s, %(active)s)
                      ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, region = EXCLUDED.region,
                      active = EXCLUDED.active""", {"active": True, **b}, conn)
    for g in client.get("goals", []):
        db.execute("""INSERT INTO core.goals (metric, period, value) VALUES (%(metric)s, %(period)s, %(value)s)
                      ON CONFLICT (metric, period) DO UPDATE SET value = EXCLUDED.value""", g, conn)


def run(dry_run: bool = False) -> int:
    settings = get_settings()
    failures = 0
    with db.connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(%s)", (LOCK_ID,))
            if not cur.fetchone()[0]:
                print("Another sync is running; exiting.")
                return 0
        conn.commit()
        try:
            if not dry_run:
                load_reference(conn, settings.client)
                conn.commit()
            for src in settings.client.get("sources", []):
                connector = REGISTRY[src["type"]](src)
                for spec in connector.objects():
                    started = time.monotonic()
                    try:
                        rows = list(spec.fetch())
                        if dry_run:
                            print(f"{spec.name:28} {len(rows):7} rows fetched (dry run)")
                            continue
                        upserted, pruned, warning = sync_object(conn, spec, rows)
                        status = "warning" if warning else "ok"
                        msg = warning or f"{time.monotonic() - started:.1f}s"
                        _record(conn, spec, connector.source, status, msg, len(rows), upserted, pruned)
                        conn.commit()
                        print(f"{spec.name:28} {len(rows):7} seen {upserted:7} written {pruned:5} removed  {status}")
                        if warning:
                            print("   ", warning)
                    except Exception as e:  # one object failing must not stop the rest
                        conn.rollback()
                        failures += 1
                        _record(conn, spec, connector.source, "failed", str(e)[:500])
                        conn.commit()
                        print(f"{spec.name:28} FAILED: {e}", file=sys.stderr)
        finally:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_unlock(%s)", (LOCK_ID,))
            conn.commit()
    return 1 if failures else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Sync all sources into the database.")
    p.add_argument("--dry-run", action="store_true")
    sys.exit(run(p.parse_args().dry_run))
