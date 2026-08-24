"""Keep the privacy and cookie pages honest.

Those pages promise no cookies, no analytics and no third-party requests. If
someone later adds a web font or an embedded script, the promise silently
becomes false. These tests fail instead.
"""
import re
from pathlib import Path

import pytest

SITE = Path(__file__).resolve().parents[1] / "site"

# Hosts that would load third-party code or leak the visitor's IP.
TRACKER_PATTERNS = [
    "google-analytics", "googletagmanager", "gtag(", "ga(", "fbq(",
    "facebook.net", "hotjar", "mixpanel", "segment.com", "amplitude",
    "plausible.io", "matomo", "clarity.ms", "doubleclick", "sentry.io",
    "fonts.googleapis.com", "fonts.gstatic.com", "cdn.jsdelivr.net",
    "cdnjs.cloudflare.com", "unpkg.com", "ajax.googleapis.com",
]

# Prose may link to these; they are navigation, not loaded resources.
ALLOWED_LINK_HOSTS = ("doi.org", "openneuro.org", "vercel.com", "github.com",
                      "en.wikipedia.org", "arxiv.org", "nature.com",
                      "academic.oup.com", "sciencedirect.com", "jneurosci.org",
                      "pnas.org", "ieeexplore.ieee.org", "s3.amazonaws.com")


def html_files():
    return sorted(SITE.glob("*.html"))


@pytest.mark.parametrize("path", html_files(), ids=lambda p: p.name)
def test_no_analytics_or_third_party_scripts(path):
    text = path.read_text().lower()
    hits = [p for p in TRACKER_PATTERNS if p.lower() in text]
    assert not hits, f"{path.name} loads {hits}, which the privacy page denies"


@pytest.mark.parametrize("path", html_files(), ids=lambda p: p.name)
def test_no_externally_loaded_resources(path):
    """src= and stylesheet href= must stay on this origin."""
    html = path.read_text()
    srcs = re.findall(r'<(?:script|img|iframe|video|audio|embed|source)[^>]*\ssrc=["\']([^"\']+)', html, re.I)
    sheets = re.findall(r'<link[^>]*rel=["\']stylesheet["\'][^>]*href=["\']([^"\']+)', html, re.I)
    preloads = re.findall(r'<link[^>]*rel=["\'](?:preconnect|dns-prefetch|preload)["\'][^>]*href=["\']([^"\']+)', html, re.I)
    for url in srcs + sheets + preloads:
        assert not url.startswith(("http://", "https://", "//")), \
            f"{path.name} loads {url} from another host"


@pytest.mark.parametrize("path", html_files(), ids=lambda p: p.name)
def test_outbound_links_go_where_we_say(path):
    for url in re.findall(r'<a[^>]*href=["\'](https?://[^"\']+)', path.read_text(), re.I):
        host = url.split("/")[2]
        assert any(host.endswith(h) for h in ALLOWED_LINK_HOSTS), \
            f"{path.name} links to unexpected host {host}"


@pytest.mark.parametrize("path", html_files(), ids=lambda p: p.name)
def test_no_cookie_or_storage_calls(path):
    text = path.read_text()
    for bad in ("document.cookie", "localStorage", "sessionStorage", "indexedDB"):
        assert bad not in text, f"{path.name} uses {bad}, which the cookie page denies"


def test_required_legal_pages_exist():
    for name in ("privacy.html", "terms.html", "cookies.html", "accessibility.html"):
        p = SITE / name
        assert p.is_file() and p.stat().st_size > 1500, f"{name} missing or too short"


def test_every_page_links_to_the_legal_pages():
    for path in html_files():
        html = path.read_text()
        for name in ("privacy.html", "terms.html", "cookies.html", "accessibility.html"):
            assert name in html, f"{path.name} does not link to {name}"


def test_medical_disclaimer_is_on_every_page():
    for path in html_files():
        text = path.read_text().lower()
        assert "not medical advice" in text or "medical advice" in text, \
            f"{path.name} has no medical disclaimer"


def test_pages_declare_language_and_viewport():
    for path in html_files():
        html = path.read_text()
        assert '<html lang="en">' in html, f"{path.name} missing lang attribute"
        assert 'name="viewport"' in html, f"{path.name} missing viewport meta"
        assert '<a class="skip"' in html, f"{path.name} missing skip link"


def test_no_preview_or_synthetic_results_are_published():
    """Guard against a rehearsal file reaching the live site.

    While building the interactive chart a synthetic results file was written so
    the layout could be checked before real numbers existed. Publishing that
    would put invented figures on a page about real people's brain scans.
    """
    import json
    results = Path(__file__).resolve().parents[1] / "results"
    for p in results.glob("*.json"):
        try:
            d = json.loads(p.read_text())
        except json.JSONDecodeError:
            continue
        if isinstance(d, dict):
            assert not d.get("_preview"), f"{p.name} is a preview file"
            assert not d.get("synthetic"), f"{p.name} is marked synthetic"
            for sub in d.get("subjects", []) or []:
                s = str(sub.get("sub", ""))
                assert not s.startswith(("sub-9", "sub-8")), \
                    f"{p.name} contains test subject {s}"
