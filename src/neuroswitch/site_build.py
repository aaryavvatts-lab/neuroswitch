"""Generate the static site from results/*.json.

The site is generated rather than hand-written so that no number on a page can
drift from the number the analysis actually produced.  Pages render in a
"pending" state when a result file is absent, which keeps the site buildable at
every point during a long pipeline run.

The look is the shared design system used across the author's sites: one
typeface (Erode, self-hosted), a light and a dark palette that follow the
visitor's system setting with a text control to override it, square corners,
no decorative lines.  The kit files (tokens.css, base.css, fonts.css, kit.js,
theme-head.js, fonts/) are committed under site/ and are not touched here.
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
REPO = "https://github.com/aaryavvatts-lab/neuroswitch"

# One long article plus a tools page, rather than eight thin pages.
PAGES = [
    ("index.html", "The study"),
    ("explore.html", "Try it"),
]

# In-page anchors for the article, listed as contents beside the title.
ANCHORS = [
    ("#built", "What I built"),
    ("#data", "The data"),
    ("#signal", "Is the signal real"),
    ("#pipeline", "From scans to networks"),
    ("#models", "How the models work"),
    ("#answer", "Does the graph network win"),
    ("#wrong", "Four ways this could be wrong"),
    ("#learned", "What the model learned"),
    ("#multiverse", "The same data, ninety ways"),
    ("#limits", "What is wrong with this"),
    ("#run", "Run it yourself"),
    ("#refs", "References"),
]

# Linked from the footer rather than the main nav.
LEGAL_PAGES = [
    ("privacy.html", "Privacy"),
    ("terms.html", "Terms"),
    ("cookies.html", "Cookies"),
    ("accessibility.html", "Accessibility"),
]

# Found pictures, with the credit each one carries. The files live in site/img
# and credits.json next to them records the same facts.
CREDITS = (
    'Pictures: <a href="https://commons.wikimedia.org/wiki/File:A_series_of_engravings,'
    '_explaining_the_course_of_the_nerves_-_with_an_address_to_young_physicians_on_the_study'
    '_of_the_nerves_(1818)_(14774983314).jpg">nerves of the arm</a>, Charles Bell, 1818, '
    'no known copyright restrictions, via Wikimedia Commons; '
    '<a href="https://commons.wikimedia.org/wiki/File:Anatomy,_descriptive_and_surgical_(1887)'
    '_(14763598044).jpg">nerves of the right arm</a> from Gray\'s Anatomy, 1887 edition, '
    'no known copyright restrictions, via Wikimedia Commons; '
    '<a href="https://www.rawpixel.com/image/6261472/image-vintage-public-domain-art">'
    'the nervous system, 19th century engraving</a>, CC0, via rawpixel; '
    '<a href="https://commons.wikimedia.org/wiki/File:MRI-Philips.JPG">MRI scanner in '
    'Gothenburg</a> by Jan Ainali, <a href="https://creativecommons.org/licenses/by/3.0">'
    'CC BY 3.0</a>, via Wikimedia Commons. The brain region pictures are drawn from this '
    'project\'s own region file. Type is Erode by Indian Type Foundry, under the '
    '<a href="https://www.fontshare.com/licenses/itf-ffl">ITF Free Font License</a>.'
)


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
    return (f'<li><span class="figs__n">{n}</span>'
            f'<span class="figs__k">{e(k)}</span></li>')


def stats(items) -> str:
    """A row of figures, each with a sentence-case caption at reading size."""
    return '<ul class="figs">' + "".join(stat(n, k) for n, k in items) + "</ul>"


def bars(rows, lo=0.4, hi=1.0) -> str:
    """rows: (label, value, is_null). Chance line drawn at 0.5."""
    out = ['<div class="bars">']
    span = hi - lo
    chance = (0.5 - lo) / span * 100
    i = 0
    for label, val, is_null in rows:
        if val is None:
            continue
        pct = max(0.0, min(1.0, (val - lo) / span)) * 100
        cls = " is-null" if is_null else ""
        out.append(
            f'<div class="auc{cls}" style="--i:{i}"><div class="lab">{e(label)}</div>'
            f'<div class="track"><div class="fill" style="width:{pct:.1f}%"></div>'
            f'<div class="chance" style="left:{chance:.1f}%"></div></div>'
            f'<div class="val">{val:.3f}</div></div>')
        i += 1
    out.append('</div><p class="small">Bars span AUC 0.40-1.00; '
               'the vertical line is chance (0.50). Grey bars are control models '
               'that <em>should</em> stay near chance.</p>')
    return "".join(out)


def picture(stem: str, alt: str, width: int, height: int, cls: str = "",
            lazy: bool = True) -> str:
    """A theme-aware pair of pictures: stem-light.png and stem-dark.png."""
    lz = ' loading="lazy"' if lazy else ""
    c = f' {cls}' if cls else ""
    return (f'<img class="only-light{c}" src="img/{stem}-light.png" width="{width}" '
            f'height="{height}" alt="{e(alt)}"{lz} decoding="async">'
            f'<img class="only-dark{c}" src="img/{stem}-dark.png" width="{width}" '
            f'height="{height}" alt="{e(alt)}"{lz} decoding="async">')


def page(fname: str, title: str, body: str, lede: str = "",
         anchors: bool = False) -> str:
    def links(cur=True):
        return "".join(
            f'<a href="{h}"{" aria-current=\"page\"" if (cur and h == fname) else ""}>'
            f'{e(t)}</a>' for h, t in PAGES)

    sheet_links = "".join(
        f'<a href="{h}"{" aria-current=\"page\"" if h == fname else ""} '
        f'style="--i:{i}">{e(t)}</a>'
        for i, (h, t) in enumerate(PAGES + LEGAL_PAGES))
    legal = "".join(
        f'<a href="{h}"{" aria-current=\"page\"" if h == fname else ""}>{e(t)}</a>'
        for h, t in LEGAL_PAGES)
    desc = e(lede[:180] if lede else title)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#f4f3ef">
<title>{e(title)} · neuroswitch</title>
<meta name="description" content="{desc}">
<meta name="robots" content="index, follow">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="article">
<meta property="og:image" content="https://hand-injury-brain-rewiring.vercel.app/img/bell-nerves-1818.jpg">
<script src="theme-head.js"></script>
<link rel="stylesheet" href="fonts.css">
<link rel="stylesheet" href="tokens.css">
<link rel="stylesheet" href="base.css">
<link rel="stylesheet" href="style.css">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<script src="kit.js" defer></script>
</head>
<body>
<a class="skip" href="#main">Skip to main content</a>
<header class="wrap bar">
<a class="bar__mark" href="index.html">neuroswitch</a>
<nav class="bar__links" aria-label="Site">{links()}
<button class="theme" type="button" data-theme-toggle aria-pressed="false">Light</button>
</nav>
<div class="bar__phone">
<button class="theme" type="button" data-theme-toggle aria-pressed="false">Light</button>
<button class="bar__menu textbtn" type="button" data-menu-toggle aria-expanded="false" aria-controls="menu">Menu</button>
</div>
</header>
<nav id="menu" class="sheet" hidden aria-label="Menu">
<div class="sheet__top"><span class="bar__mark">neuroswitch</span>
<button class="textbtn" type="button" data-menu-close>Close</button></div>
<div class="sheet__links">{sheet_links}</div>
<p class="small">Brain networks after nerve injury. A student reanalysis.</p>
</nav>
<main id="main">
{body}
</main>
<footer class="wrap close">
<p class="close__mark">neuroswitch</p>
<p>Built from <a href="{DS_DOI}">OpenNeuro ds008162</a>, released under CC0 by
Kapil, Kim, McAvoy and Philip at Washington University in St. Louis. This is a
student reanalysis. It is not connected to that group and they have not reviewed it.
Page built {date.today().isoformat()}.</p>
<p>This is a student project. It is not medical advice and it is not a medical
device. If you have a hand or nerve problem, talk to a doctor.</p>
<nav class="close__meta" aria-label="Legal and site">{links(cur=False)}{legal}
<a href="{REPO}">Code</a></nav>
<p class="small credits">{CREDITS}</p>
</footer>
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
