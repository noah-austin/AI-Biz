"""Turn the AI's answer (light Markdown) into safe HTML.

Everything is escaped first; then only a few patterns are turned back into markup:
**bold**, bullet and numbered lists, and links whose target is a path in this hub
or a source-system link template from the client config. Anything else stays text.
"""
import html
import re

from ..config import get_settings

LINK = re.compile(r"\[([^\]\n]{1,200})\]\(([^)\s]{1,600})\)")
BOLD = re.compile(r"\*\*([^*\n]{1,300})\*\*")


def _allowed(href: str) -> bool:
    href = html.unescape(href)
    if href.startswith("/") and not href.startswith("//") and "\\" not in href:
        return True
    for tmpl in get_settings().client.get("links", {}).values():
        prefix = tmpl.split("{", 1)[0]
        if prefix.startswith("https://") and href.startswith(prefix):
            return True
    return False


def _inline(text: str) -> str:
    out = html.escape(text, quote=True)

    def link(m):
        label, href = m.group(1), m.group(2)
        if not _allowed(href):
            return label
        external = not html.unescape(href).startswith("/") or html.unescape(href).startswith("/demo-source/")
        target = ' target="_blank" rel="noopener"' if external else ""
        return f'<a href="{href}"{target}>{label}</a>'

    out = LINK.sub(link, out)
    return BOLD.sub(r"<strong>\1</strong>", out)


def to_html(text: str) -> str:
    blocks, items, kind = [], [], None

    def flush():
        nonlocal items, kind
        if items:
            tag = "ol" if kind == "ol" else "ul"
            blocks.append(f"<{tag}>" + "".join(f"<li>{i}</li>" for i in items) + f"</{tag}>")
        items, kind = [], None

    for raw in (text or "").strip().splitlines():
        line = raw.strip()
        bullet = re.match(r"^[-*•]\s+(.*)", line)
        number = re.match(r"^\d+[.)]\s+(.*)", line)
        if bullet or number:
            this = "ol" if number else "ul"
            if kind and kind != this:
                flush()
            kind = this
            items.append(_inline((bullet or number).group(1)))
            continue
        flush()
        if not line:
            continue
        heading = re.match(r"^#{1,4}\s+(.*)", line)
        if heading:
            blocks.append(f"<p><strong>{_inline(heading.group(1))}</strong></p>")
        elif line.lower().startswith("how i counted:"):
            blocks.append(f'<p class="counted">{_inline(line)}</p>')
        else:
            blocks.append(f"<p>{_inline(line)}</p>")
    flush()
    return "".join(blocks)
