"""Charts for the site, written as SVG by hand.

Matplotlib would produce a raster with a baked-in background, which looks wrong
when the reader's system is in dark mode. These are plain SVG using CSS custom
properties, so they follow the page theme and stay sharp at any zoom.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
FIGS = ROOT / "site" / "figures"


def _esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def _load(name):
    p = RESULTS / f"{name}.json"
    return json.loads(p.read_text()) if p.is_file() else None


def _svg(w: int, h: int, body: str, title: str, desc: str = "",
        slug: str = "fig") -> str:
    # width/height give the file an intrinsic size, which matters if a page
    # ever references one of these by <img> again. The ids are prefixed per
    # figure because the site inlines the <svg> markup directly into the
    # article rather than loading it as a standalone document, so multiple
    # figures share one page and duplicate ids would break aria-labelledby
    # for everything after the first.
    tid, did = f"{slug}-t", f"{slug}-d"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
            f'width="{w}" height="{h}" '
            f'role="img" aria-labelledby="{tid} {did}" '
            f'font-family="system-ui, sans-serif">'
            f'<title id="{tid}">{_esc(title)}</title>'
            f'<desc id="{did}">{_esc(desc)}</desc>'
            f'{body}</svg>')


def lateralisation_figure() -> str | None:
    """Left minus right response for the parcels that separate the hands most."""
    san = _load("sanity_lateralisation")
    if not san or not san.get("top_left_hand"):
        return None
    left = san["top_left_hand"][:8]
    right = list(reversed(san["top_right_hand"][:8]))
    rows = right + left
    if not rows:
        return None

    w, h = 720, 40 + len(rows) * 26 + 40
    lab_w, mid = 250, 250 + (w - 270) / 2
    span = max(abs(r["value"]) for r in rows) or 1.0
    half = (w - lab_w - 30) / 2

    parts = [f'<line x1="{mid}" y1="26" x2="{mid}" y2="{h-42}" '
             f'stroke="var(--rule)" stroke-width="1"/>']
    parts.append(f'<text x="{mid - half}" y="18" font-size="11" fill="var(--ink-2)">'
                 f'more active drawing with the RIGHT hand</text>')
    parts.append(f'<text x="{mid + 6}" y="18" font-size="11" fill="var(--ink-2)">'
                 f'more active drawing with the LEFT hand</text>')

    for i, r in enumerate(rows):
        y = 34 + i * 26
        name = r["name"].replace("17Networks_", "").replace("_", " ")
        side = r["hemi"]
        colour = "var(--right)" if side == "RH" else "var(--left)"
        length = abs(r["value"]) / span * half
        x = mid if r["value"] >= 0 else mid - length
        parts.append(f'<text x="{lab_w - 8}" y="{y + 12}" font-size="11.5" '
                     f'text-anchor="end" fill="var(--ink)">{_esc(name[:34])}</text>')
        parts.append(f'<rect x="{x:.1f}" y="{y + 3}" width="{length:.1f}" height="14" '
                     f'rx="2" fill="{colour}" fill-opacity="0.85"/>')
        tag = "R" if side == "RH" else "L" if side == "LH" else "mid"
        tx = mid + length + 6 if r["value"] >= 0 else mid - length - 6
        anchor = "start" if r["value"] >= 0 else "end"
        parts.append(f'<text x="{tx:.1f}" y="{y + 14}" font-size="10" '
                     f'text-anchor="{anchor}" fill="var(--ink-3)">{tag}</text>')

    parts.append(f'<text x="{lab_w}" y="{h - 16}" font-size="11" fill="var(--ink-2)">'
                 f'Blue bars sit in the right half of the brain, orange in the left. '
                 f'The sides swap with the drawing hand.</text>')
    return _svg(w, h, "".join(parts),
                "Left hand minus right hand response by brain region",
                "Regions more active during left hand drawing are mostly on the right "
                "side of the brain, and the reverse for the right hand.",
                slug="lateralisation")


def motion_figure() -> str | None:
    """Head movement per person, split by group, against the cut-off."""
    coh = _load("cohort")
    if not coh:
        return None
    subs = [s for s in coh.get("subjects", []) if s.get("mean_fd")]
    if len(subs) < 4:
        return None
    pat = sorted(s["mean_fd"] for s in subs if s.get("is_patient") == 1)
    ctl = sorted(s["mean_fd"] for s in subs if s.get("is_patient") == 0)
    if not pat or not ctl:
        return None

    w, h = 720, 210
    x0, x1 = 60, w - 30
    hi = max(max(pat), max(ctl), 0.32) * 1.12
    sx = lambda v: x0 + (v / hi) * (x1 - x0)

    parts = []
    for frac in (0.0, 0.1, 0.2, 0.3):
        if frac > hi:
            continue
        x = sx(frac)
        parts.append(f'<line x1="{x:.1f}" y1="34" x2="{x:.1f}" y2="150" '
                     f'stroke="var(--rule)" stroke-dasharray="2 4"/>')
        parts.append(f'<text x="{x:.1f}" y="168" font-size="10.5" text-anchor="middle" '
                     f'fill="var(--ink-3)">{frac:.1f}</text>')
    xc = sx(0.30)
    parts.append(f'<line x1="{xc:.1f}" y1="28" x2="{xc:.1f}" y2="150" '
                 f'stroke="var(--stop)" stroke-width="1.5"/>')
    parts.append(f'<text x="{xc + 5:.1f}" y="26" font-size="10.5" fill="var(--stop)">'
                 f'runs above 0.30 mm are dropped</text>')

    for row, (vals, name, colour, y) in enumerate((
            (pat, f"patients (n={len(pat)})", "var(--right)", 60),
            (ctl, f"controls (n={len(ctl)})", "var(--left)", 110))):
        parts.append(f'<text x="{x0 - 10}" y="{y + 4}" font-size="11.5" '
                     f'text-anchor="end" fill="var(--ink)">{_esc(name)}</text>')
        for v in vals:
            parts.append(f'<circle cx="{sx(v):.1f}" cy="{y}" r="4" fill="{colour}" '
                         f'fill-opacity="0.5"/>')
        med = vals[len(vals) // 2]
        parts.append(f'<line x1="{sx(med):.1f}" y1="{y - 12}" x2="{sx(med):.1f}" '
                     f'y2="{y + 12}" stroke="var(--ink)" stroke-width="2"/>')

    parts.append(f'<text x="{(x0 + x1) / 2:.0f}" y="192" font-size="11" '
                 f'text-anchor="middle" fill="var(--ink-2)">'
                 f'average head movement per image (mm). '
                 f'The thick line is the middle value for each group.</text>')
    return _svg(w, h, "".join(parts), "Head movement by group",
                "Each dot is one person. The vertical red line marks the cut-off.",
                slug="motion")


def build_all() -> dict:
    FIGS.mkdir(parents=True, exist_ok=True)
    made = {}
    for name, fn in (("lateralisation", lateralisation_figure),
                     ("motion", motion_figure)):
        svg = fn()
        if svg:
            (FIGS / f"{name}.svg").write_text(svg)
            made[name] = f"figures/{name}.svg"
    return made


if __name__ == "__main__":
    m = build_all()
    print(f"{len(m)} figures written" if m else "no figures yet (results missing)")
    for k, v in m.items():
        print(f"  {k}: {(ROOT / 'site' / v).stat().st_size} bytes")
