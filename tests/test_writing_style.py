"""Guard the prose against the patterns that read as machine-written.

Checks the built HTML against the specific tells listed in Wikipedia's
"Signs of AI writing" essay: a vocabulary that clusters around a small set of
inflated words, negative parallelisms, editorialising throat-clearing, em dashes,
curly quotes and title-case headings.
"""
import re
from pathlib import Path

import pytest

SITE = Path(__file__).resolve().parents[1] / "site"

# Flagged vocabulary. Words that are fine in a normal sentence are matched only
# in the constructions the essay actually calls out.
BANNED_WORDS = [
    "delve", "delves", "delving", "tapestry", "testament", "underscore",
    "underscores", "underscoring", "showcase", "showcases", "showcasing",
    "pivotal", "vibrant", "robust", "seamless", "seamlessly", "leverage",
    "leveraging", "realm", "landscape of", "intricate", "meticulous",
    "meticulously", "garner", "garnered", "bolster", "bolstered",
    "multifaceted", "myriad", "plethora", "paradigm shift", "game-changer",
    "cutting-edge", "state-of-the-art", "groundbreaking", "unwavering",
    "profound", "profoundly", "boasts", "nestled", "rich cultural",
    "deep dive", "interplay", "foster a", "fostering", "resonate",
    "resonates", "align with", "aligns with", "holistic", "synergy",
    "navigate the", "navigating the", "embark", "harness", "harnessing",
    "transformative", "invaluable", "indelible", "ever-evolving",
]

BANNED_PHRASES = [
    "it is worth noting", "it's worth noting", "it is important to note",
    "it's important to note", "importantly,", "notably,", "crucially,",
    "in conclusion", "in summary", "overall,", "furthermore,", "moreover,",
    "additionally,", "that being said", "at the end of the day",
    "plays a vital role", "plays a crucial role", "plays a key role",
    "serves as a", "stands as a", "a testament to", "sheds light on",
    "paving the way", "sets the stage", "in the realm of", "when it comes to",
    "one of the most", "a wide range of", "a diverse array",
]

# "not just X but Y" and friends
NEGATIVE_PARALLELISM = re.compile(
    r"\bnot (only|just|merely|simply)\b[^.]{0,80}?\bbut\b", re.I)


def html_files():
    return sorted(SITE.glob("*.html"))


def visible_text(path: Path) -> str:
    """Body text only. <head> is dropped so asset URLs cannot leak into checks."""
    t = path.read_text()
    t = re.sub(r"<head.*?</head>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<script.*?</script>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t)


def test_site_was_built():
    assert len(html_files()) >= 12, "run neuroswitch.site_build first"


@pytest.mark.parametrize("path", html_files(), ids=lambda p: p.name)
def test_no_em_or_en_dashes(path):
    text = visible_text(path)
    assert "—" not in text, f"em dash in {path.name}"
    assert "–" not in text, f"en dash in {path.name}"


@pytest.mark.parametrize("path", html_files(), ids=lambda p: p.name)
def test_no_curly_quotes(path):
    text = visible_text(path)
    for ch, name in (("“", "left double"), ("”", "right double"),
                     ("‘", "left single"), ("’", "right single")):
        assert ch not in text, f"curly {name} quote in {path.name}"


@pytest.mark.parametrize("path", html_files(), ids=lambda p: p.name)
def test_no_flagged_vocabulary(path):
    text = visible_text(path).lower()
    hits = [w for w in BANNED_WORDS if re.search(rf"\b{re.escape(w)}\b", text)]
    assert not hits, f"{path.name}: {hits}"


@pytest.mark.parametrize("path", html_files(), ids=lambda p: p.name)
def test_no_flagged_phrases(path):
    text = visible_text(path).lower()
    hits = [p for p in BANNED_PHRASES if p in text]
    assert not hits, f"{path.name}: {hits}"


@pytest.mark.parametrize("path", html_files(), ids=lambda p: p.name)
def test_no_negative_parallelism(path):
    m = NEGATIVE_PARALLELISM.search(visible_text(path))
    assert m is None, f"{path.name}: {m.group(0)!r}"


@pytest.mark.parametrize("path", html_files(), ids=lambda p: p.name)
def test_headings_are_sentence_case(path):
    """Title Case In Every Word is one of the listed tells."""
    for tag in ("h1", "h2", "h3"):
        for raw in re.findall(rf"<{tag}[^>]*>(.*?)</{tag}>", path.read_text(), re.S | re.I):
            head = re.sub(r"<[^>]+>", "", raw).strip()
            words = [w for w in re.findall(r"[A-Za-z][A-Za-z'-]+", head) if len(w) > 3]
            if len(words) < 4:
                continue
            capped = sum(1 for w in words if w[0].isupper())
            assert capped < len(words) * 0.8, f"{path.name}: title case heading {head!r}"


@pytest.mark.parametrize("path", html_files(), ids=lambda p: p.name)
def test_sentence_length_varies(path):
    """Uniform sentence length is a hallmark of generated prose."""
    text = visible_text(path)
    lens = [len(s.split()) for s in re.split(r"(?<=[.!?]) ", text) if len(s.split()) > 3]
    if len(lens) < 12:
        return
    mean = sum(lens) / len(lens)
    sd = (sum((x - mean) ** 2 for x in lens) / len(lens)) ** 0.5
    assert sd > 5.0, f"{path.name}: sentence lengths too uniform (sd={sd:.1f})"


@pytest.mark.parametrize("path", html_files(), ids=lambda p: p.name)
def test_no_emoji_in_body_text(path):
    text = visible_text(path)
    emoji = re.findall(r"[\U0001F300-\U0001FAFF☀-➿]", text)
    assert not emoji, f"{path.name}: emoji {emoji[:3]}"


def test_stylesheet_is_plain_ascii_and_has_no_gradients():
    """Stray characters break a declaration silently; gradients are off-brief."""
    css = (SITE / "style.css").read_text()
    bad = sorted({c for c in css if ord(c) > 127})
    assert not bad, f"non-ascii characters in style.css: {bad}"
    lowered = css.lower()
    for banned in ("linear-gradient", "radial-gradient", "conic-gradient"):
        assert banned not in lowered, f"style.css uses {banned}"
    # no purple / violet hues, which read as generated-template colour
    import re as _re
    for hexcode in _re.findall(r"#([0-9a-fA-F]{6})", css):
        r, g, b = (int(hexcode[i:i + 2], 16) for i in (0, 2, 4))
        if b > r > g and (b - g) > 60 and (r - g) > 25:
            raise AssertionError(f"purple-ish colour #{hexcode} in style.css")
