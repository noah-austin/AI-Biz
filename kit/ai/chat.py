"""The "Ask" chat: a question goes in, Claude calls the hub's tools, an answer comes out.

Each question runs as a background job (reverse proxies cut requests at about 60
seconds); the page polls for the answer. The conversation history is stored
exactly as sent to the model and only ever appended to.
"""
import logging
import secrets
import threading
from decimal import Decimal

import psycopg2.extras

from .. import db, metrics
from ..config import get_settings
from ..hub.ui import date as fmt_date
from . import prompts, render, tools, usage

log = logging.getLogger("hub.ai")
MAX_STEPS = 8          # model calls per question, so a confused loop can't run up a bill
MAX_TOKENS = 16000
STALE_MINUTES = 6      # a job still "running" after this long died with its worker


def new_id() -> str:
    return secrets.token_urlsafe(12)


def _client():
    import anthropic  # imported here so the hub runs (without AI) even if the SDK isn't installed
    return anthropic.Anthropic(api_key=usage.api_key("chat"), max_retries=2, timeout=120)


def start(user: dict, question: str, conversation_id: str | None, page: str = "") -> dict:
    """Validate, create the job, and run it in a background thread. Returns ids for polling."""
    question = (question or "").strip()
    if not question:
        raise ValueError("Type a question first.")
    if len(question) > 2000:
        raise ValueError("That question is too long. Keep it under 2,000 characters.")
    if not usage.is_configured("chat"):
        raise usage.CapReached("The AI assistant isn't switched on yet. An admin needs to add its API key.")
    usage.check_caps("chat", user["id"])
    conv = None
    if conversation_id:
        conv = db.one("SELECT id FROM core.ai_conversations WHERE id = %(c)s AND user_id = %(u)s",
                      {"c": conversation_id, "u": user["id"]})
    if not conv:
        conversation_id = new_id()
        db.execute("INSERT INTO core.ai_conversations (id, user_id) VALUES (%(c)s, %(u)s)",
                   {"c": conversation_id, "u": user["id"]})
    job_id = new_id()
    db.execute("""INSERT INTO core.ai_jobs (id, conversation_id, user_id, question, progress)
                  VALUES (%(j)s, %(c)s, %(u)s, %(q)s, 'Thinking')""",
               {"j": job_id, "c": conversation_id, "u": user["id"], "q": question})
    threading.Thread(target=run_job, args=(job_id, conversation_id, user, question, page), daemon=True).start()
    return {"job_id": job_id, "conversation_id": conversation_id}


def _context_line(user: dict, page: str) -> str:
    t = metrics.today()
    who = "all branches" if not user.get("branches") else "only these branches: " + ", ".join(
        r["name"] for r in db.query("SELECT name FROM core.branches WHERE code = ANY(%(b)s) ORDER BY name",
                                    {"b": user["branches"]}))
    where = f" They're on the hub page {page}." if page and page.startswith("/") and len(page) < 300 else ""
    return f"[Today is {fmt_date(t)} ({t.isoformat()}). {user.get('name', 'This person')} can see {who}.{where}]"


def run_job(job_id: str, conversation_id: str, user: dict, question: str, page: str = "", client=None):
    """Answer one question. Saves the turn only if it finished cleanly, so the history stays valid."""
    total = Decimal("0")
    try:
        client = client or _client()
        settings = usage.ai_settings()
        row = db.one("SELECT messages FROM core.ai_conversations WHERE id = %(c)s", {"c": conversation_id})
        messages = list(row["messages"]) if row else []
        start_len = len(messages)
        messages.append({"role": "user", "content": [{"type": "text", "text": f"{_context_line(user, page)}\n\n{question}"}]})
        user_tools = tools.tools_for(user)
        system = [{"type": "text", "text": prompts.chat_system(), "cache_control": {"type": "ephemeral"}}]
        answer, keep = None, True
        for _ in range(MAX_STEPS):
            usage.check_caps("chat")  # month cap, checked before every call
            response = client.beta.messages.create(
                model=settings["model"], max_tokens=MAX_TOKENS, system=system, tools=user_tools, messages=messages,
                thinking={"type": "adaptive"}, output_config={"effort": settings["chat_effort"]},
                cache_control={"type": "ephemeral"},
                betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            )
            total += usage.record("chat", user["id"], response)
            if response.stop_reason == "refusal":
                answer = ("I can't help with that request. Try rephrasing it as a question about the company's "
                          "sales, pipeline, billing or data quality.")
                keep = False  # don't keep a declined turn in the thread
                break
            messages.append({"role": "assistant", "content": [b.to_dict(mode="json") for b in response.content]})
            if response.stop_reason == "pause_turn":
                continue
            calls = [b for b in response.content if b.type == "tool_use"]
            if response.stop_reason == "tool_use" and calls:
                results = []
                for call in calls:
                    _progress(job_id, tools.describe_call(call.name, call.input))
                    try:
                        content, is_error = tools.run(call.name, call.input, user), False
                    except tools.ToolError as e:
                        content, is_error = f"Error: {e}", True
                    except Exception:  # a bug in a tool must not leak details; the model can try another way
                        log.exception("tool %s failed", call.name)
                        content, is_error = "Error: this tool failed unexpectedly. Try a different approach.", True
                    results.append({"type": "tool_result", "tool_use_id": call.id, "content": content,
                                    "is_error": is_error})
                messages.append({"role": "user", "content": results})
                _progress(job_id, "Writing the answer")
                continue
            answer = "\n\n".join(b.text for b in response.content if b.type == "text").strip()
            if response.stop_reason == "max_tokens":
                answer += "\n\n(The answer was cut off. Ask a narrower question.)"
            break
        else:
            answer = "That question needed more steps than I'm allowed. Try breaking it into smaller questions."
            keep = False
        if keep:
            db.execute("""UPDATE core.ai_conversations SET messages = %(m)s, updated_at = now()
                          WHERE id = %(c)s AND jsonb_array_length(messages) = %(n)s""",
                       {"m": psycopg2.extras.Json(messages), "c": conversation_id, "n": start_len})
        db.execute("""UPDATE core.ai_jobs SET status = 'done', answer = %(a)s, cost_usd = %(cost)s, finished_at = now(),
                      progress = NULL WHERE id = %(j)s""", {"a": answer or "(No answer.)", "cost": total, "j": job_id})
    except usage.CapReached as e:
        _fail(job_id, str(e), total)
    except Exception as e:
        log.exception("AI job %s failed", job_id)
        _fail(job_id, _friendly(e), total)


def _friendly(e: Exception) -> str:
    name = type(e).__name__
    if name == "AuthenticationError":
        return "The AI's API key was rejected. An admin needs to check it."
    if name == "RateLimitError":
        return "The AI is busy right now. Try again in a minute."
    if name in ("APIConnectionError", "APITimeoutError"):
        return "Couldn't reach the AI service. Try again in a minute."
    return "Something went wrong answering that. Try again, or ask it a different way."


def _progress(job_id, text):
    db.execute("UPDATE core.ai_jobs SET progress = %(p)s WHERE id = %(j)s", {"p": text, "j": job_id})


def _fail(job_id, message, cost):
    db.execute("""UPDATE core.ai_jobs SET status = 'failed', error = %(e)s, cost_usd = %(c)s, finished_at = now(),
                  progress = NULL WHERE id = %(j)s""", {"e": message, "c": cost, "j": job_id})


def job_status(job_id: str, user: dict) -> dict | None:
    db.execute(f"""UPDATE core.ai_jobs SET status = 'failed', error = 'This answer was interrupted. Please ask again.',
                   finished_at = now() WHERE status = 'running' AND created_at < now() - interval '{STALE_MINUTES} minutes'""")
    j = db.one("""SELECT id, conversation_id, question, status, progress, answer, error FROM core.ai_jobs
                  WHERE id = %(j)s AND user_id = %(u)s""", {"j": job_id, "u": user["id"]})
    if not j:
        return None
    return {"status": j["status"], "progress": j["progress"], "question": j["question"],
            "answer_html": render.to_html(j["answer"]) if j["answer"] else None, "error": j["error"]}


def history(conversation_id: str, user: dict) -> list[dict]:
    rows = db.query("""SELECT question, status, answer, error FROM core.ai_jobs
                       WHERE conversation_id = %(c)s AND user_id = %(u)s AND status <> 'running'
                       ORDER BY created_at""", {"c": conversation_id, "u": user["id"]})
    return [{"question": r["question"], "answer_html": render.to_html(r["answer"]) if r["answer"] else None,
             "error": r["error"]} for r in rows]


def suggestions(user: dict) -> list[str]:
    base = ["How are we doing this year compared with last year?",
            "Which big deals were won or lost this week, and why?",
            "Where do we win the most money?",
            "Which customers should we call about late invoices?"]
    if not user.get("branches"):
        base.insert(2, "Which branch has the most data to clean up?")
    return base
