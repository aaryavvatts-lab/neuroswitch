"""Privacy, terms, cookie and accessibility pages.

The site is static and collects nothing, so these say so plainly instead of
copying boilerplate that would describe data handling that does not happen.
"""
from __future__ import annotations

from datetime import date

from .site_build import DS_DOI, write

UPDATED = date.today().isoformat()


def build_privacy() -> None:
    body = f"""
<h1>Privacy</h1>
<p class="lede">Short version. This site does not collect anything about you.</p>

<section>
<h2>What we collect</h2>
<div class="measure">
<p>Nothing. There is no sign-up, no login, no contact form, and no comment box.
The site is a set of plain HTML files. There is no database behind it and no
account for you to have.</p>
<p>We do not run analytics. There is no Google Analytics, no Meta pixel, no
heatmap tool, and no session recorder. We do not know who visits or what pages
they read.</p>
<p>We do not use advertising, and we do not sell or share data with anyone,
because we do not have any data to sell or share.</p>
</div>
</section>

<section>
<h2>What the host can see</h2>
<div class="measure">
<p>The site is hosted on Vercel. Like any web host, their servers keep short
request logs so the service can run and stay secure. Those logs can include your
IP address, the page you asked for, the time, and your browser's user agent
string. We do not open those logs, and we do not link them to anything.</p>
<p>If you want to know how the host handles that, read Vercel's own privacy
policy at <a href="https://vercel.com/legal/privacy-policy">vercel.com/legal/privacy-policy</a>.</p>
</div>
</section>

<section>
<h2>Links out</h2>
<div class="measure">
<p>Pages link to papers and to the dataset. Those sites are run by other people,
usually publishers or universities, and they have their own rules. Once you click
away, this policy stops applying.</p>
</div>
</section>

<section>
<h2>Whose brain scans are these?</h2>
<div class="measure">
<p>None of the brain data on this site belongs to a person you could identify.
The scans come from <a href="{DS_DOI}">OpenNeuro dataset ds008162</a>. Everyone in
that study agreed to have their de-identified data shared. Faces were stripped
from the structural scans by the original team using pydeface before release.</p>
<p>This site never shows an individual brain image. Everything shown is a group
average or a summary number. Subject codes like sub-1001 appear in the code and in
the public dataset, but they are the codes the original team assigned and they do
not point back to a real name.</p>
</div>
</section>

<section>
<h2>Children</h2>
<div class="measure">
<p>The site is not aimed at children and collects nothing from anyone, including
children.</p>
</div>
</section>

<section>
<h2>Your rights</h2>
<div class="measure">
<p>Rules like the GDPR and the CCPA give you the right to see, correct or delete
personal data a site holds about you. We hold none, so there is nothing to show
you and nothing to delete. If you think that is wrong, get in touch through the
GitHub repository linked from the References page and we will look into it.</p>
</div>
</section>

<section>
<h2>Changes</h2>
<div class="measure">
<p>If this ever changes, the date below changes with it.</p>
<p class="small">Last updated {UPDATED}.</p>
</div>
</section>
"""
    write("privacy.html", "Privacy", body,
          "This site collects nothing. No analytics, no cookies, no accounts.")


def build_terms() -> None:
    body = f"""
<h1>Terms of use</h1>
<p class="lede">A student project, shared as is. Read it, learn from it, do not
treat it as medical advice.</p>

<section>
<h2>What this is</h2>
<div class="measure">
<p>This is a student reanalysis of a public brain imaging dataset. It is a
learning project. It has not been peer reviewed, it has not been checked by the
team who collected the data, and no journal has accepted it.</p>
</div>
</section>

<section>
<h2>Not medical advice</h2>
<div class="note bad">
<p>Nothing here diagnoses, treats or predicts any condition in any person. The
models are trained on 66 people from one scanner. They are not a medical device
and must not be used to make decisions about anyone's care. If you have hand pain,
nerve damage, or any other health problem, see a qualified clinician.</p>
</div>
</section>

<section>
<h2>No warranty</h2>
<div class="measure">
<p>The site and the code are provided as is, with no promise that they are
correct, complete or fit for anything in particular. Numbers may change as more
data is processed. Bugs are possible, and some have already been found and fixed
during the work. Use it at your own risk.</p>
<p>To the extent the law allows, the author is not liable for any loss that comes
from using this site or the code.</p>
</div>
</section>

<section>
<h2>Using the material</h2>
<div class="measure">
<p>The underlying scans come from <a href="{DS_DOI}">OpenNeuro ds008162</a> and are
released under CC0, which means the original team placed them in the public domain.
Credit for collecting that data belongs to Kapil, Kim, McAvoy and Philip at
Washington University in St. Louis.</p>
<p>The analysis code in the linked repository is released under the MIT licence.
You can reuse it. If you build on the writing or figures here, a link back is
appreciated.</p>
<p>Papers linked from the References page belong to their publishers. Follow the
links to read them under whatever terms those publishers set.</p>
</div>
</section>

<section>
<h2>Fair use of the site</h2>
<div class="measure">
<p>Please do not scrape the site in a way that hammers the host, and do not
present the content as though it came from the original research team or from
Washington University.</p>
</div>
</section>

<section>
<h2>Governing law</h2>
<div class="measure">
<p>These terms are governed by the laws of the United States and the State of
Minnesota, without regard to conflict of law rules.</p>
<p class="small">Last updated {UPDATED}.</p>
</div>
</section>
"""
    write("terms.html", "Terms of use", body,
          "Student project shared as is. Not medical advice. MIT licensed code.")


def build_cookies() -> None:
    body = f"""
<h1>Cookies</h1>
<p class="lede">This site does not set any cookies. That is why you never saw a
cookie banner.</p>

<section>
<h2>Why there is no banner</h2>
<div class="measure">
<p>Cookie banners exist because sites store things in your browser and track you
across pages. This site does neither. There are no cookies, no local storage, no
session storage, and no tracking pixels. Every page is a plain HTML file that
loads and then sits there.</p>
<p>Under the EU ePrivacy rules and the GDPR, consent is needed before a site
stores or reads information on your device unless it is strictly necessary. Since
nothing is stored or read, there is nothing to ask you about, and showing a banner
anyway would be noise.</p>
</div>
</section>

<section>
<h2>What the pages actually load</h2>
<div class="measure">
<p>Each page loads one stylesheet and, on the brain page, one small JSON file with
region coordinates. Both come from this same site. There are no fonts, scripts,
images or frames pulled in from anywhere else, so no third party learns that you
visited.</p>
</div>
</section>

<section>
<h2>The one bit of JavaScript</h2>
<div class="measure">
<p>The brain page runs a small script so you can filter regions and click on them.
It runs entirely in your browser. It sends nothing anywhere and remembers nothing
after you close the tab. If you block JavaScript, the rest of the site still works
and that one page shows a short message instead of the map.</p>
</div>
</section>

<section>
<h2>How to check</h2>
<div class="measure">
<p>You do not have to take our word for it. Open your browser's developer tools,
go to the storage or application tab, and look at the cookie list for this domain.
It should be empty. The network tab will show every request the page makes.</p>
<p class="small">Last updated {UPDATED}.</p>
</div>
</section>
"""
    write("cookies.html", "Cookies", body,
          "No cookies, no local storage, no third-party requests. Nothing to consent to.")


def build_accessibility() -> None:
    body = f"""
<h1>Accessibility</h1>
<p class="lede">The aim is WCAG 2.1 level AA. Here is what has been done and what
is still weak.</p>

<section>
<h2>What has been done</h2>
<div class="measure">
<p>Pages use real headings in order, so a screen reader can jump through the
structure. Every page starts with a skip link that takes you straight to the main
content. Tables use proper header cells. The main navigation is marked as
navigation and the current page is flagged.</p>
<p>Text and background colours were picked to pass the AA contrast ratio in both
the light and dark themes. The site follows whatever theme your system is set to
rather than forcing one.</p>
<p>Nothing is measured only in pixels, so browser zoom and larger default font
sizes work. The layout reflows down to a phone screen without a sideways scroll
bar. Wide tables scroll inside their own box instead of pushing the page around.</p>
<p>Colour is never the only signal. Control models in the results table are
labelled in text as well as shown in grey.</p>
</div>
</section>

<section>
<h2>The brain map</h2>
<div class="measure">
<p>The interactive map on the Explore page is the hardest part to make accessible.
Each region can be reached with the Tab key and opened with Enter or Space, and
each one has a text label a screen reader can read. Network filters are real
buttons.</p>
<p>Even so, a scatter plot of 241 dots is a visual thing. For that reason every
number the map shows is also given as a plain table underneath it, ranked in
order. If the map does not work for you, the table has the same information.</p>
</div>
</section>

<section>
<h2>Motion</h2>
<div class="measure">
<p>There is no animation, no autoplay, no parallax and no carousel. The site also
respects the reduce motion setting if your system has one turned on.</p>
</div>
</section>

<section>
<h2>Where it falls short</h2>
<div class="measure">
<p>Being honest about the gaps:</p>
<p>The brain map has no audio description, and a sighted reader will get more from
it than a screen reader user, even with the table.</p>
<p>Some region names are compressed atlas labels such as SomMotB S2 2. They are
hard to read out loud and hard to understand without background knowledge. The
full name is given in the detail panel, but it is still jargon.</p>
<p>The site has not been tested with every screen reader. It has been checked for
keyboard navigation, heading order and contrast, but not on JAWS or Dragon.</p>
</div>
</section>

<section>
<h2>Tell us</h2>
<div class="measure">
<p>If something here blocks you, open an issue on the GitHub repository linked
from the References page and describe what happened. That is the fastest way to
get it fixed.</p>
<p class="small">Last updated {UPDATED}.</p>
</div>
</section>
"""
    write("accessibility.html", "Accessibility", body,
          "Aiming for WCAG 2.1 AA. What works, and where the site still falls short.")
