"""Cost tracking and spending caps for every AI feature."""
import datetime as dt
import os
from decimal import Decimal

from .. import db
from ..config import _load_env_file, env_file, get_settings

# $ per million tokens: input, output, cache read, cache write (5-minute).
PRICES = {
    "claude-opus-5-5": (4.00, 20.00, 0.20, 5.00),
    "claude-opus-5": (5.00, 25.00, 0.50, 6.25),
    "claude-opus-4-8": (5.00, 25.00, 0.50, 6.25),
    "claude-sonnet-5-5": (2.00, 10.00, 0.20, 2.50),
}
DEFAULT_PRICE = (5.00, 25.00, 0.50, 6.25)  # unknown model: assume the dearer end, never under-count

FEATURES = {"chat": "ANTHROPIC_API_KEY_CHAT", "insights": "ANTHROPIC_API_KEY_INSIGHTS",
            "agents": "ANTHROPIC_API_KEY_AGENTS"}
WEB_SEARCH_USD = 0.01  # per search (estimate: $10 per 1,000)


class CapReached(RuntimeError):
    """Raised before a call that would go over a cap. The message is safe to show to users."""


def ai_settings() -> dict:
    defaults = {"model": "claude-opus-5-5", "chat_effort": "medium", "insights_effort": "high",
                "chat_monthly_cap_usd": 50, "insights_monthly_cap_usd": 25, "agents_monthly_cap_usd": 60,
                "questions_per_user_per_day": 40, "insights_per_day": 3}
    return {**defaults, **get_settings().client.get("ai", {})}


def api_key(feature: str) -> str | None:
    """Each feature has its own key; ANTHROPIC_API_KEY is only a fallback for local testing."""
    _load_env_file(env_file())
    return os.environ.get(FEATURES[feature]) or os.environ.get("ANTHROPIC_API_KEY") or None


def is_configured(feature: str) -> bool:
    return bool(api_key(feature))


def cost_of(model: str, usage) -> Decimal:
    p_in, p_out, p_read, p_write = PRICES.get(model, DEFAULT_PRICE)
    get = lambda name: getattr(usage, name, 0) or 0
    dollars = (get("input_tokens") * p_in + get("output_tokens") * p_out
               + get("cache_read_input_tokens") * p_read + get("cache_creation_input_tokens") * p_write) / 1_000_000
    searches = getattr(getattr(usage, "server_tool_use", None), "web_search_requests", 0) or 0
    dollars += searches * WEB_SEARCH_USD
    return Decimal(str(round(dollars, 6)))


def record(feature: str, user_id, response) -> Decimal:
    """Log one API response. Returns its cost."""
    usage = response.usage
    cost = cost_of(response.model, usage)
    db.execute("""INSERT INTO core.ai_usage (feature, user_id, model, input_tokens, output_tokens, cache_read_tokens,
                                             cache_write_tokens, cost_usd, request_id)
                  VALUES (%(f)s, %(u)s, %(m)s, %(i)s, %(o)s, %(cr)s, %(cw)s, %(c)s, %(r)s)""",
               {"f": feature, "u": user_id, "m": response.model, "i": usage.input_tokens or 0,
                "o": usage.output_tokens or 0, "cr": getattr(usage, "cache_read_input_tokens", 0) or 0,
                "cw": getattr(usage, "cache_creation_input_tokens", 0) or 0, "c": cost,
                "r": getattr(response, "_request_id", None)})
    return cost


def month_spend(feature: str) -> float:
    r = db.one("""SELECT coalesce(sum(cost_usd), 0) AS c FROM core.ai_usage
                  WHERE feature = %(f)s AND at >= date_trunc('month', now() AT TIME ZONE core.client_tz())
                                                     AT TIME ZONE core.client_tz()""", {"f": feature})
    return float(r["c"])


def check_caps(feature: str, user_id=None):
    s = ai_settings()
    cap = float(s[f"{feature}_monthly_cap_usd"])
    if month_spend(feature) >= cap:
        raise CapReached(f"The AI {feature} budget for this month (${cap:,.0f}) is used up. "
                         "It resets on the 1st, or an admin can raise the cap.")
    if feature == "chat" and user_id is not None:
        n = db.one("""SELECT count(*) AS n FROM core.ai_jobs WHERE user_id = %(u)s
                      AND created_at >= (core.local_today()::timestamp AT TIME ZONE core.client_tz())""",
                   {"u": user_id})["n"]
        if n >= int(s["questions_per_user_per_day"]):
            raise CapReached(f"You've asked {n} questions today, which is the daily limit. It resets at midnight.")


def summary() -> list[dict]:
    """This month's spend per feature, for the Health page."""
    s = ai_settings()
    out = []
    for feature in FEATURES:
        r = db.one("""SELECT count(*) AS calls, coalesce(sum(cost_usd), 0) AS cost,
                             coalesce(sum(input_tokens + cache_read_tokens + cache_write_tokens), 0) AS tokens_in,
                             coalesce(sum(output_tokens), 0) AS tokens_out
                      FROM core.ai_usage WHERE feature = %(f)s
                        AND at >= date_trunc('month', now() AT TIME ZONE core.client_tz()) AT TIME ZONE core.client_tz()""",
                   {"f": feature})
        jobs = db.one("""SELECT count(*) AS n, coalesce(avg(cost_usd), 0) AS avg_cost FROM core.ai_jobs
                         WHERE status = 'done' AND created_at > now() - interval '30 days'""") if feature == "chat" else None
        out.append({"feature": feature, "configured": is_configured(feature), "calls": r["calls"],
                    "cost": float(r["cost"]), "cap": float(s[f"{feature}_monthly_cap_usd"]),
                    "tokens_in": int(r["tokens_in"]), "tokens_out": int(r["tokens_out"]),
                    "answers_30d": jobs["n"] if jobs else None,
                    "avg_answer_cost": float(jobs["avg_cost"]) if jobs else None})
    return out
