"""Settings for one client install.

Secrets and machine settings come from the environment (or a root-only .env
file next to the repo). Business settings come from the client folder's
config.toml. Anything required that's missing stops start-up with a clear
message, instead of failing later in a confusing way.
"""
import os
import tomllib
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = ["DATABASE_URL", "SESSION_SECRET", "CLIENT_DIR"]


class ConfigError(RuntimeError):
    pass


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass
class Settings:
    database_url: str
    session_secret: str
    client_dir: Path
    ai_reader_password: str | None
    secure_cookies: bool
    client: dict = field(repr=False)

    @property
    def tz(self) -> str:
        return self.client.get("timezone", "America/Chicago")

    @property
    def is_demo(self) -> bool:
        return bool(self.client.get("demo", False))


@lru_cache
def get_settings() -> Settings:
    _load_env_file(ROOT / ".env")
    missing = [k for k in REQUIRED if not os.environ.get(k)]
    if missing:
        raise ConfigError(f"Missing required settings: {', '.join(missing)}. See .env.example.")
    if len(os.environ["SESSION_SECRET"]) < 32:
        raise ConfigError("SESSION_SECRET must be at least 32 characters.")
    client_dir = Path(os.environ["CLIENT_DIR"])
    if not client_dir.is_absolute():
        client_dir = ROOT / client_dir
    cfg_path = client_dir / "config.toml"
    if not cfg_path.exists():
        raise ConfigError(f"No config.toml in {client_dir}")
    client = tomllib.loads(cfg_path.read_text())
    return Settings(
        database_url=os.environ["DATABASE_URL"],
        session_secret=os.environ["SESSION_SECRET"],
        client_dir=client_dir,
        ai_reader_password=os.environ.get("AI_READER_PASSWORD") or None,
        secure_cookies=os.environ.get("SECURE_COOKIES", "1") != "0",
        client=client,
    )
