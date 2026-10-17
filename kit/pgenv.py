"""Print safe shell exports (PGHOST, PGUSER, ...) for the database in .env.

The ops scripts use this instead of sourcing .env as shell code, and so the
password travels in the environment rather than on the command line (where
any user on the server could see it in the process list).

    eval "$(python3 -m kit.pgenv)"                      # from DATABASE_URL
    eval "$(python3 -m kit.pgenv RESTORE_ADMIN_URL)"    # from another variable
"""
import os
import shlex
import sys
from urllib.parse import parse_qs, unquote, urlparse

from .config import _load_env_file, env_file


def main():
    _load_env_file(env_file())
    var = sys.argv[1] if len(sys.argv) > 1 else "DATABASE_URL"
    url = os.environ.get(var)
    if not url:
        sys.exit(f"{var} is not set")
    u = urlparse(url)
    env = {"PGHOST": u.hostname, "PGPORT": u.port, "PGUSER": unquote(u.username or ""),
           "PGPASSWORD": unquote(u.password or ""), "PGDATABASE": u.path.lstrip("/")}
    for k, v in parse_qs(u.query).items():
        if k == "sslmode":
            env["PGSSLMODE"] = v[0]
    for k, v in env.items():
        if v not in (None, ""):
            print(f"export {k}={shlex.quote(str(v))}")
    for k in ("BACKUP_DIR", "KEEP_DAYS", "OFFSITE_CMD"):
        if os.environ.get(k):
            print(f"export {k}={shlex.quote(os.environ[k])}")


if __name__ == "__main__":
    main()
