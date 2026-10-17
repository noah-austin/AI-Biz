"""Small form system for data entry: draw a form from a list of fields, then read and check what was typed.

Every value is escaped when drawn and validated when read; nothing typed goes into SQL except as a parameter.
"""
import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from . import auth
from .ui import esc


@dataclass
class Field:
    name: str
    label: str
    kind: str = "text"          # text, textarea, select, date, money, number, checkbox, email, url, tel
    required: bool = False
    options: list = field(default_factory=list)   # [(value, label)] for select
    hint: str = ""
    wide: bool = False
    default: object = None
    max_len: int = 500


class FormError(ValueError):
    def __init__(self, errors: dict):
        super().__init__("; ".join(errors.values()))
        self.errors = errors


def render(request, fields: list[Field], values: dict | None = None, action: str = "", submit: str = "Save",
           errors: dict | None = None, extra: str = "") -> str:
    values = values or {}
    errors = errors or {}
    parts = []
    for f in fields:
        v = values.get(f.name, f.default)
        v = "" if v is None else v
        err = f'<span class="field-err">{esc(errors[f.name])}</span>' if f.name in errors else ""
        req = " required" if f.required else ""
        star = ' <span class="req" aria-hidden="true">*</span>' if f.required else ""
        if f.kind == "textarea":
            control = f'<textarea name="{f.name}" rows="3" maxlength="{f.max_len * 8}"{req}>{esc(v)}</textarea>'
        elif f.kind == "select":
            opts = "".join(f'<option value="{esc(ov)}"{" selected" if str(ov) == str(v) else ""}>{esc(ol)}</option>'
                           for ov, ol in f.options)
            control = f'<select name="{f.name}"{req}>{opts}</select>'
        elif f.kind == "checkbox":
            checked = " checked" if v in (True, "on", "true", "1", 1) else ""
            parts.append(f'<label class="check-field"><input type="checkbox" name="{f.name}"{checked}> {esc(f.label)}</label>')
            continue
        else:
            html_type = {"date": "date", "money": "number", "number": "number", "email": "email", "url": "url",
                         "tel": "tel"}.get(f.kind, "text")
            step = ' step="0.01" min="0" inputmode="decimal"' if f.kind == "money" else (' step="0.25" min="0" inputmode="decimal"' if f.kind == "number" else "")
            if isinstance(v, (dt.date,)):
                v = v.isoformat()
            control = f'<input type="{html_type}" name="{f.name}" value="{esc(v)}" maxlength="{f.max_len}"{step}{req}>'
        hint = f'<span class="hint">{esc(f.hint)}</span>' if f.hint else ""
        parts.append(f'<label class="field{" wide" if f.wide or f.kind == "textarea" else ""}">'
                     f'<span>{esc(f.label)}{star}</span>{control}{hint}{err}</label>')
    token = auth.csrf_token(request.cookies.get(auth.COOKIE))
    return (f'<form method="post" action="{esc(action)}" class="entry-form"><input type="hidden" name="_csrf" value="{token}">'
            f'<div class="form-grid">{"".join(parts)}</div>{extra}'
            f'<div class="form-actions"><button class="primary" type="submit">{esc(submit)}</button></div></form>')


def parse(fields: list[Field], form) -> dict:
    out, errors = {}, {}
    for f in fields:
        raw = form.get(f.name)
        if raw is None and f.default is not None and f.kind != "checkbox":
            raw = f.default.isoformat() if isinstance(f.default, dt.date) else str(f.default)  # field not sent at all
        raw = raw.strip() if isinstance(raw, str) else raw
        if f.kind == "checkbox":
            out[f.name] = raw in ("on", "true", "1")
            continue
        if raw in (None, ""):
            if f.required:
                errors[f.name] = f"{f.label} is required."
            out[f.name] = None
            continue
        if len(raw) > (f.max_len * 8 if f.kind == "textarea" else f.max_len):
            errors[f.name] = f"{f.label} is too long."
            continue
        try:
            if f.kind == "date":
                out[f.name] = dt.date.fromisoformat(raw)
            elif f.kind in ("money", "number"):
                n = Decimal(raw.replace(",", "").replace("$", ""))
                if n < 0 or n > Decimal("100000000"):
                    raise InvalidOperation
                out[f.name] = n
            elif f.kind == "select":
                allowed = {str(v) for v, _ in f.options}
                if raw not in allowed:
                    raise ValueError
                out[f.name] = raw
            elif f.kind == "url" and not raw.startswith(("http://", "https://")):
                out[f.name] = "https://" + raw
            else:
                out[f.name] = raw
        except (ValueError, InvalidOperation):
            errors[f.name] = f"{f.label} doesn't look right."
    if errors:
        raise FormError(errors)
    return out
