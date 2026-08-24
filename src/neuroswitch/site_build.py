"""Generate the static site from results/*.json.

The site is generated rather than hand-written so that no number on a page can
drift from the number the analysis actually produced.  Pages render in a
"pending" state when a result file is absent, which keeps the site buildable at
every point during a long pipeline run.
"""
from __future__ import annotations

import html
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
SITE = ROOT / "site"

DS_DOI = "https://doi.org/10.18112/openneuro.ds008162.v1.0.3"
PREPRINT = "https://doi.org/10.1101/2025.11.18.689091"

# One long article plus a tools page, rather than eight thin pages.
PAGES = [
    ("index.html", "The study"),
    ("explore.html", "Try it"),
]

# In-page anchors for the article, shown as a secondary row.
ANCHORS = [
    ("#built", "What I built"),
    ("#data", "The data"),
    ("#signal", "Is the signal real"),
    ("#pipeline", "Pipeline"),
    ("#models", "Models"),
    ("#answer", "The answer"),
    ("#wrong", "Could it be wrong"),
    ("#learned", "What it learned"),
    ("#multiverse", "Ninety pipelines"),
    ("#limits", "What is wrong with this"),
    ("#run", "Run it"),
    ("#refs", "References"),
]

# Linked from the footer rather than the main nav.
LEGAL_PAGES = [
    ("privacy.html", "Privacy"),
    ("terms.html", "Terms"),
    ("cookies.html", "Cookies"),
    ("accessibility.html", "Accessibility"),
]


# ------------------------------------------------------------------ helpers
def e(s) -> str:
    return html.escape(str(s), quote=True)


def load(name: str):
    p = RESULTS / f"{name}.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return None


def fmt_auc(v) -> str:
    return "n/a" if v is None else f"{v:.3f}"


def fmt_ci(ci) -> str:
    if not ci or ci[0] is None or (isinstance(ci[0], float) and ci[0] != ci[0]):
        return ""
    return f"{ci[0]:.2f}-{ci[1]:.2f}"


def fmt_p(p) -> str:
    if p is None:
        return "n/a"
    if p < 0.001:
        return "&lt;0.001"
    return f"{p:.3f}"


def pending(msg="Not worked out yet. The pipeline is still running.") -> str:
    return f'<p class="pending">{e(msg)}</p>'


def stat(n, k) -> str:
    return f'<div class="stat"><div class="n">{n}</div><div class="k">{e(k)}</div></div>'


def stats(items) -> str:
    return '<div class="stats">' + "".join(stat(n, k) for n, k in items) + "</div>"


def bars(rows, lo=0.4, hi=1.0) -> str:
    """rows: (label, value, is_null). Chance line drawn at 0.5."""
    out = ['<div class="bars">']
    span = hi - lo
    chance = (0.5 - lo) / span * 100
    for label, val, is_null in rows:
        if val is None:
            continue
        pct = max(0.0, min(1.0, (val - lo) / span)) * 100
        cls = " is-null" if is_null else ""
        out.append(
            f'<div class="bar{cls}"><div class="lab">{e(label)}</div>'
            f'<div class="track"><div class="fill" style="width:{pct:.1f}%"></div>'
            f'<div class="chance" style="left:{chance:.1f}%"></div></div>'
            f'<div class="val">{val:.3f}</div></div>')
    out.append('</div><p class="small">Bars span AUC 0.40-1.00; '
               'the vertical line is chance (0.50). Grey bars are control models '
               'that <em>should</em> stay near chance.</p>')
    return "".join(out)


def page(fname: str, title: str, body: str, lede: str = "",
         anchors: bool = False) -> str:
    nav = "".join(
        f'<a href="{h}"{" aria-current=\"page\"" if h == fname else ""}>{e(t)}</a>'
        for h, t in PAGES)
    legal = " · ".join(
        f'<a href="{h}"{" aria-current=\"page\"" if h == fname else ""}>{e(t)}</a>'
        for h, t in LEGAL_PAGES)
    sub = ""
    if anchors:
        sub = ('<div class="subnav"><div class="wrap"><nav aria-label="Sections">'
               + "".join(f'<a href="{h}">{e(t)}</a>' for h, t in ANCHORS)
               + "</nav></div></div>")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} · neuroswitch</title>
<meta name="description" content="{e(lede[:180] if lede else title)}">
<meta name="robots" content="index, follow">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(lede[:180] if lede else title)}">
<meta property="og:type" content="article">
<link rel="stylesheet" href="style.css">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
</head>
<body>
<a class="skip" href="#main">Skip to main content</a>
<header class="site"><div class="wrap">
<a class="brand" href="index.html">neuroswitch<span> · brain networks after nerve injury</span></a>
<nav class="site" aria-label="Main">{nav}</nav>
</div></header>
{sub}
<main class="wrap" id="main">
{body}
</main>
<footer class="site"><div class="wrap">
<p>Built from <a href="{DS_DOI}">OpenNeuro ds008162</a>, released under CC0 by
Kapil, Kim, McAvoy and Philip at Washington University in St. Louis. This is a
student reanalysis. It is not connected to that group and they have not reviewed it.
Page built {date.today().isoformat()}.</p>
<p>This is a student project. It is not medical advice and it is not a medical
device. If you have a hand or nerve problem, talk to a doctor.</p>
<p class="legal"><a href="index.html">The study</a> · <a href="explore.html">Try it</a> · {legal}</p>
</div></footer>
</body>
</html>
"""


def write(fname: str, title: str, body: str, lede: str = "",
          anchors: bool = False) -> None:
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / fname).write_text(page(fname, title, body, lede, anchors))


def build_all() -> None:
    from . import pages
    from .export_site import build as build_data_json
    try:
        build_data_json()
    except Exception as exc:            # site must still build before results exist
        print(f"  (brain data export skipped: {exc!r})")
    from . import legal
    from .figures import build_all as build_figures
    try:
        build_figures()
    except Exception as exc:
        print(f"  (figures skipped: {exc!r})")
    for fn in (pages.build_index, pages.build_explore,
               legal.build_privacy, legal.build_terms, legal.build_cookies,
               legal.build_accessibility):
        fn()
    for stale in ("data.html", "methods.html", "results.html", "brain.html",
                  "controls.html", "reproduce.html", "refs.html"):
        (SITE / stale).unlink(missing_ok=True)
    n = len(PAGES) + len(LEGAL_PAGES)
    print(f"built {n} pages -> {SITE}")


if __name__ == "__main__":
    build_all()
