# Brand: Sanford Operations

## Logo
The **seal**: "SANFORD" across the top, "OPERATIONS" along the bottom, a star either side, a serif S in the centre. Chosen 2026-10-18 (concept "Engraved Roundel, split name"). No date or place on it.

| File (`website/static/brand/`) | Use it for |
|---|---|
| `lockup.svg` / `lockup-reversed.svg` | Seal + name side by side: website header, proposals, letterhead. Reversed = on dark backgrounds. |
| `seal.svg` / `seal-reversed.svg` | The seal on its own (lines only). |
| `seal-solid.svg`, `profile-800.png` | Filled oxblood seal: LinkedIn, Google Workspace and other profile pictures. |
| `mark.svg`, `mark-512.png`, `apple-touch-icon.png` | Small sizes (browser tab, phone home screen). No edge lettering, because it can't be read that small. |
| `email-signature.png` | The lockup for the email signature (`website/brand/email-signature.html`). |
| `seal-1024.png` | Large transparent PNG for documents and slides. |

Rebuild after changes: `python website/brand/build.py`, then `node website/brand/render_png.js` (PNG sizes).

**Rules:** keep clear space around the seal of at least the width of the S. Don't stretch, recolour outside the palette, add effects, or put the line version on busy photos (use the solid one). Below 48px, use `mark.svg`.

## Colours
| Name | Hex | Use |
|---|---|---|
| Oxblood | `#6b1f2a` | The seal, buttons, links, headings accents |
| Parchment | `#f5efe4` | Backgrounds, the seal on dark |
| Ink | `#2a2622` | Body text, "Operations" in the lockup |

## Type
- **Logo and headings:** Playfair Display (bold; italic for "Operations").
- **Body text:** Inter.

Both are free (SIL Open Font License); copies and licences are in `website/brand/fonts/` and `website/static/fonts/`.
