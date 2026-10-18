"""Builds the Sanford Operations logo files into website/static/brand/.

    python website/brand/build.py

All lettering is converted to outlines, so the files look the same everywhere (browsers, email, social sites)
without the font installed. Font: Playfair Display (SIL Open Font License, see fonts/Playfair-LICENSE.txt).
Colours and usage: docs/brand.md.
"""
import math
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

HERE = Path(__file__).parent
OUT = HERE.parent / "static" / "brand"
OXBLOOD, PARCHMENT, INK = "#6b1f2a", "#f5efe4", "#2a2622"
C = 32  # the seal is drawn on a 64 x 64 grid


class Face:
    def __init__(self, file):
        self.font = TTFont(HERE / "fonts" / file)
        self.glyphs = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()
        self.upm = self.font["head"].unitsPerEm

    def advance(self, ch, size):
        return self.font["hmtx"][self.cmap[ord(ch)]][0] * size / self.upm

    def path(self, ch, size, x=0.0, y=0.0):
        """SVG path data for one glyph, baseline-left at (x, y)."""
        if ch == " ":
            return ""
        s = size / self.upm
        pen = SVGPathPen(self.glyphs, ntos=lambda n: f"{n:.2f}".rstrip("0").rstrip("."))
        self.glyphs[self.cmap[ord(ch)]].draw(TransformPen(pen, (s, 0, 0, -s, x, y)))
        return pen.getCommands()

    def width(self, text, size, spacing):
        return sum(self.advance(c, size) for c in text) + spacing * (len(text) - 1)

    def line(self, text, size, x, y, spacing=0.0, anchor="start"):
        if anchor == "middle":
            x -= self.width(text, size, spacing) / 2
        out = []
        for ch in text:
            out.append(self.path(ch, size, x, y))
            x += self.advance(ch, size) + spacing
        return " ".join(p for p in out if p)

    def arc(self, text, size, radius, spacing, where="top"):
        """Text centred on the top of a circle (reading left to right), or along the bottom (upright)."""
        total = self.width(text, size, spacing)
        parts, s = [], 0.0
        for ch in text:
            adv = self.advance(ch, size)
            mid = s + adv / 2 - total / 2           # distance from the centre of the text
            if where == "top":
                theta = math.pi / 2 - mid / radius
                rot = 90 - math.degrees(theta)
            else:
                theta = 3 * math.pi / 2 + mid / radius
                rot = 270 - math.degrees(theta)
            px, py = C + radius * math.cos(theta), C - radius * math.sin(theta)
            d = self.path(ch, size, -adv / 2, 0)
            if d:
                parts.append(f'<path transform="translate({px:.3f} {py:.3f}) rotate({rot:.3f})" d="{d}"/>')
            s += adv + spacing
        return "".join(parts)


BOLD = Face("playfair-display-latin-700-normal.woff2")
ITALIC = Face("playfair-display-latin-400-italic.woff2")


def star(x, y, r):
    pts = []
    for k in range(10):
        a = -math.pi / 2 + k * math.pi / 5
        rr = r if k % 2 == 0 else r * 0.42
        pts.append(f"{x + rr * math.cos(a):.3f},{y + rr * math.sin(a):.3f}")
    return f'<polygon points="{" ".join(pts)}"/>'


def ring(r, w, colour):
    return f'<circle cx="{C}" cy="{C}" r="{r}" fill="none" stroke="{colour}" stroke-width="{w}"/>'


def seal(ink, disc=None):
    """The full seal: SANFORD across the top, OPERATIONS along the bottom, stars at the sides, S in the centre."""
    body = [f'<circle cx="{C}" cy="{C}" r="30.8" fill="{disc}"/>'] if disc else []
    outer = (29.5, 0.7) if disc else (30, 1.6)
    body += [ring(outer[0], outer[1], ink), ring(19.5, 0.9, ink),
             f'<g fill="{ink}">',
             BOLD.arc("SANFORD", 6.4, 23.4, 3.2, "top"),
             BOLD.arc("OPERATIONS", 5.2, 27.6, 2.2, "bottom"),
             star(C - 24.8, C, 2.1), star(C + 24.8, C, 2.1),
             f'<path d="{BOLD.line("S", 22, C, C + 7.7, anchor="middle")}"/>',
             "</g>"]
    return "".join(body)


def mark(ink=PARCHMENT, disc=OXBLOOD):
    """Small-size icon: no lettering around the edge, just the disc, one ring and the S."""
    return (f'<circle cx="{C}" cy="{C}" r="31" fill="{disc}"/>{ring(26.5, 1.6, ink)}'
            f'<path fill="{ink}" d="{BOLD.line("S", 36, C, C + 12.6, anchor="middle")}"/>')


def svg(body, w=64, h=64, title="Sanford Operations"):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-label="{title}">'
            f"<title>{title}</title>{body}</svg>\n")


def lockup(ink=OXBLOOD, sub=INK):
    """Seal + name side by side, for the website header, proposals and letterhead."""
    name = BOLD.line("SANFORD", 30, 76, 36, spacing=4.2)
    ops = ITALIC.line("Operations", 17, 77, 56)
    return svg(f'{seal(ink)}<path fill="{ink}" d="{name}"/><path fill="{sub}" d="{ops}"/>', w=262, h=64)


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    files = {
        "seal.svg": svg(seal(OXBLOOD)),
        "seal-reversed.svg": svg(seal(PARCHMENT)),
        "seal-solid.svg": svg(seal(PARCHMENT, disc=OXBLOOD)),
        "mark.svg": svg(mark()),
        "lockup.svg": lockup(),
        "lockup-reversed.svg": lockup(PARCHMENT, "#e9dcc9"),
    }
    for name, content in files.items():
        (OUT / name).write_text(content)
    return sorted(files)


# PNG sizes made by website/brand/render_png.js (needs Playwright): see docs/brand.md.
PNGS = [("seal.svg", 1024, "seal-1024.png"), ("seal-solid.svg", 800, "profile-800.png"),
        ("mark.svg", 180, "apple-touch-icon.png"), ("mark.svg", 512, "mark-512.png"),
        ("lockup.svg", 600, "email-signature.png")]


if __name__ == "__main__":
    for f in build():
        print("wrote", OUT / f)
