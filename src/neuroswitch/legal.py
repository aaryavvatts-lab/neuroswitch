"""Privacy, terms, cookie and accessibility pages.

The site is static and collects nothing, so these describe what actually
happens rather than copying boilerplate about data handling that does not
exist. They are written to be read, not to be skipped.
"""
from __future__ import annotations

from datetime import date

from .site_build import DS_DOI, write

UPDATED = date.today().isoformat()
REPO = "https://github.com/aaryavvatts-lab/neuroswitch"


def build_privacy() -> None:
    body = f"""
<h1>Privacy</h1>
<p class="lede">The short version: this site does not collect anything about you.
There is no analytics, no tracking, no account, and no database. The long version
explains what that means in practice and what the host can still see.</p>

<section>
<h2>Who runs this</h2>
<div class="measure">
<p>This is a student project run by one person. It is not a company, it has no
employees, and it makes no money. There is no marketing list, no customer record
and no third party being paid for anything.</p>
<p>The site is a set of static HTML files. It has no server-side code of its own, no
login, no comment box, no contact form, no search that talks to a server, and no
shopping of any kind.</p>
</div>
</section>

<section>
<h2>What this site collects</h2>
<div class="measure">
<p>Nothing. To be specific, because "nothing" is easy to write and often untrue:</p>
</div>
<ul class="flaws">
<li><strong>No analytics.</strong> There is no Google Analytics, no Plausible, no
Fathom, no Matomo, no Vercel Analytics, no Meta pixel, no TikTok pixel, no LinkedIn
tag and no advertising script of any kind.</li>
<li><strong>No cookies.</strong> The site sets none. See the
<a href="cookies.html">cookies page</a> for how to check this yourself in about
twenty seconds.</li>
<li><strong>No local storage.</strong> Nothing is written to localStorage,
sessionStorage or IndexedDB. Close the tab and no trace remains.</li>
<li><strong>No fingerprinting.</strong> No canvas fingerprinting, no font
enumeration, no device probing.</li>
<li><strong>No third-party requests.</strong> Every file a page loads comes from
this same site. There are no web fonts from Google, no scripts from a CDN, no
embedded videos and no iframes. That matters because a request to another company's
server tells that company your IP address and which page you were reading, even if
this site never sees it.</li>
<li><strong>No accounts.</strong> There is nothing to sign up for, so there is no
email address, name or password to lose.</li>
</ul>
<div class="measure">
<p>There are automated tests in the repository that check the built pages for
analytics scripts, third-party resources, cookie calls and storage calls. If someone
later adds a web font or a tracking tag, those tests fail and the claim on this page
stops being quietly false. That is the only way a promise like this stays true over
time.</p>
</div>
</section>

<section>
<h2>What the host can see</h2>
<div class="measure">
<p>The site is hosted on Vercel. Like any web host, their servers keep short request
logs so the service can run, stay online and resist abuse. Those logs can include
your IP address, the page you requested, the time of the request, the response code
and your browser's user agent string.</p>
<p>This is ordinary infrastructure logging and it happens for every website you have
ever visited. I do not open those logs, I do not export them, and I have not
connected them to anything. I could not identify a visitor from them and have no
interest in doing so.</p>
<p>Vercel acts as the host here. Their own policy governs what they do with that
data, and it is worth reading if you care:
<a href="https://vercel.com/legal/privacy-policy">vercel.com/legal/privacy-policy</a>.
If you would rather they saw nothing at all, a VPN or Tor will hide your address
from them, and the site works fine either way because it needs no scripts to read.</p>
</div>
</section>

<section>
<h2>Links to other sites</h2>
<div class="measure">
<p>The study page links to research papers, mostly through DOI links that resolve to
publishers such as Nature, Oxford University Press, Elsevier and the Society for
Neuroscience. It also links to OpenNeuro, to GitHub and to Vercel.</p>
<p>Those are other people's websites with their own rules and, in most cases, their
own tracking. Once you click away from here, this policy stops applying and theirs
begins. Nothing on this site is loaded from any of them, so simply reading a page
here does not tell any of them anything.</p>
</div>
</section>

<section>
<h2>Whose brain scans are these?</h2>
<div class="measure">
<p>This is the part that deserves the most care, because the underlying data came
from real people who agreed to something specific.</p>
<p>The scans come from <a href="{DS_DOI}">OpenNeuro dataset ds008162</a>, collected at
Washington University in St. Louis. Everyone in that study consented to having their
de-identified data shared publicly, and it was released under a CC0 licence by the
team who collected it. That consent is theirs, given to that team, and this project
relies on it rather than asking for anything new.</p>
<p>Before release, the original team removed facial features from the structural
scans using a tool called pydeface. That matters because a high-resolution head scan
can otherwise be rendered into a recognisable face.</p>
<p>This site never shows an individual person's brain image. Everything you see is
either a group average, a summary number, or a map of standard anatomical regions
that is the same for everyone. Codes such as <code>sub-1001</code> appear in the code
and in the public dataset, but they are labels the original team assigned during
recruitment and they do not lead back to a name.</p>
<p>The pipeline also deletes its copies of the raw scans as it goes, keeping only
extracted region signals. That was originally a disk-space decision, but it also
means this project holds far less identifiable material than it otherwise would.</p>
</div>
</section>

<section>
<h2>Children</h2>
<div class="measure">
<p>This site is not directed at children, and since it collects nothing from anyone,
it collects nothing from children either. It does not knowingly hold personal
information about anyone of any age. Everyone in the underlying dataset was an
adult.</p>
</div>
</section>

<section>
<h2>Your rights under GDPR, UK GDPR and CCPA</h2>
<div class="measure">
<p>If you are in the European Union, the United Kingdom, California or one of the
other places with a modern privacy law, you have rights over personal data a site
holds about you. Those typically include the right to know what is held, to get a
copy, to have mistakes corrected, to have it deleted, to object to processing, and
not to be sold to anyone.</p>
<p>I hold no personal data about visitors, so there is nothing to disclose, nothing
to correct, nothing to delete and nothing to opt out of. Your data has never been
sold or shared because it has never been collected.</p>
<p>If you think that is wrong, or you want to raise something, open an issue on the
<a href="{REPO}">project repository</a>. For anything about the host's own logs,
Vercel is the party to ask.</p>
<p>There is no legitimate-interest balancing test to describe and no legal basis to
declare, because there is no processing of personal data taking place on this end.</p>
</div>
</section>

<section>
<h2>Security</h2>
<div class="measure">
<p>Pages are served over HTTPS. There is no login to compromise and no stored
personal data to breach. The worst realistic outcome of someone gaining access would
be defacement of the published pages, which would be visible immediately and fixed
by redeploying from the public repository.</p>
</div>
</section>

<section>
<h2>Changes to this policy</h2>
<div class="measure">
<p>If the site ever starts collecting anything, this page changes first and the date
below changes with it. Given that it is a static research write-up, that is unlikely.
The full history of every version of this page is public in the repository, so you
can check what it said on any past date rather than taking my word for it.</p>
<p class="small">Last updated {UPDATED}.</p>
</div>
</section>
"""
    write("privacy.html", "Privacy", body,
          "This site collects nothing. No analytics, no cookies, no accounts, and no "
          "third-party requests, with tests that keep it that way.")


def build_terms() -> None:
    body = f"""
<h1>Terms of use</h1>
<p class="lede">A student project, shared as it is. Read it, learn from it, reuse the
code. Do not treat it as medical advice and do not present it as something it is
not.</p>

<section>
<h2>What this is</h2>
<div class="measure">
<p>This site is a student reanalysis of a public brain imaging dataset. It is a
learning project written by one person.</p>
<p>It has not been peer reviewed. No journal has accepted it. It has not been checked
by the team who collected the data, and they have no involvement in it. Any errors
are mine, not theirs, and the presence of their names in the credits is
acknowledgement rather than endorsement.</p>
<p>Numbers on the study page are generated automatically from analysis output and
change when the analysis is rerun. If you are citing something from here, cite the
version and check the repository history, because a figure you read last week may
not be the figure there today.</p>
</div>
</section>

<section>
<h2>Not medical advice</h2>
<div class="note bad">
<p>Nothing here diagnoses, treats, predicts or screens for any condition in any
person. The models were trained on 66 people scanned on a single machine at a single
site. They are not a medical device, they have not been validated for clinical use,
and they must not be used to make decisions about anyone's care.</p>
<p>If you have hand pain, numbness, weakness, nerve damage or any other health
concern, see a qualified clinician. Nothing on this site is a substitute for that,
and no part of it should delay you seeking care.</p>
</div>
<div class="measure">
<p>This applies to the interactive tools as much as the write-up. The replication
calculator is a teaching aid built on standard statistics. It tells you about study
designs in general. It cannot tell you whether any particular published finding is
true.</p>
</div>
</section>

<section>
<h2>No warranty</h2>
<div class="measure">
<p>The site and the code are provided as they are, with no promise that they are
correct, complete, current or fit for any particular purpose.</p>
<p>Bugs are likely. Several were found and fixed during the work, including one that
would have silently produced empty results for every completed subject and one that
made a statistical test unstable. Others probably remain. The tests in the repository
catch a useful class of mistakes and cannot catch all of them.</p>
<p>To the fullest extent the law allows, the author is not liable for any loss,
damage or cost arising from use of this site, the code, or anything derived from
either, including decisions made in reliance on them.</p>
</div>
</section>

<section>
<h2>The data, and who to credit</h2>
<div class="measure">
<p>The brain scans come from <a href="{DS_DOI}">OpenNeuro ds008162</a>, released under
CC0 by Kapil, Kim, McAvoy and Philip at Washington University in St. Louis, funded by
NINDS grant R01 NS114046. CC0 means they placed it in the public domain, which is a
generous thing to do and the only reason this project exists.</p>
<p>If you build on this, credit them for the data. Their own write-up is the
authoritative account of the study and should be read in preference to mine.</p>
</div>
</section>

<section>
<h2>Using the code and the writing</h2>
<div class="measure">
<p>The analysis code in the <a href="{REPO}">repository</a> is released under the MIT
licence. You can use it, change it, and build on it commercially, as long as the
copyright notice travels with it. There is no obligation to share your changes.</p>
<p>The writing and figures on this site are yours to quote and teach from. A link
back is appreciated but not required. What is not fine is republishing the whole
thing in a way that implies it came from Washington University, from the original
research team, or from a peer-reviewed source.</p>
<p>Papers linked from the references belong to their publishers. Follow the links and
read them under whatever terms those publishers set.</p>
</div>
</section>

<section>
<h2>Fair use of the site</h2>
<div class="measure">
<p>Please do not scrape the site in a way that hammers the host. Everything here is
also in the public repository, which is a better thing to clone if you want the
whole lot.</p>
<p>Please do not present generated numbers from this project as established
findings, and do not use the interactive tools to make claims about specific people.
</p>
</div>
</section>

<section>
<h2>Governing law</h2>
<div class="measure">
<p>These terms are governed by the laws of the State of Minnesota and the United
States, without regard to conflict of law rules. If any part of these terms is found
unenforceable, the rest continues to apply.</p>
<p class="small">Last updated {UPDATED}.</p>
</div>
</section>
"""
    write("terms.html", "Terms of use", body,
          "Student project shared as it is. Not medical advice. Code under MIT, data "
          "under CC0.")


def build_cookies() -> None:
    body = f"""
<h1>Cookies</h1>
<p class="lede">This site sets no cookies at all. That is why you never saw a banner
asking about them, and this page explains how to confirm that for yourself rather
than trusting the claim.</p>

<section>
<h2>Why there is no banner</h2>
<div class="measure">
<p>Cookie banners exist because most sites store identifiers in your browser and use
them to recognise you across pages, sessions and sometimes other websites entirely.
Under the EU ePrivacy Directive and the GDPR, and under similar rules elsewhere,
consent is required before storing or reading information on your device unless it is
strictly necessary to provide the thing you asked for.</p>
<p>This site stores nothing and reads nothing. There is no consent to collect, so a
banner would be pure theatre. Showing one anyway would train you to click through
consent dialogs without reading them, which makes the web slightly worse.</p>
</div>
</section>

<section>
<h2>What is actually stored</h2>
<div class="tablewrap"><table>
<caption>Every storage mechanism a browser offers, and what this site puts in it</caption>
<thead><tr><th>Mechanism</th><th>What this site stores</th></tr></thead>
<tbody>
<tr><td>Cookies</td><td>Nothing</td></tr>
<tr><td>Local storage</td><td>Nothing</td></tr>
<tr><td>Session storage</td><td>Nothing</td></tr>
<tr><td>IndexedDB</td><td>Nothing</td></tr>
<tr><td>Cache storage / service workers</td><td>Nothing. There is no service worker</td></tr>
<tr><td>Web SQL, app cache</td><td>Nothing. Both are obsolete anyway</td></tr>
</tbody></table></div>
<div class="measure">
<p>Your browser will cache the HTML, the stylesheet and the images the way it caches
any website, so pages load faster on a second visit. That is ordinary HTTP caching,
it holds no identifier, and clearing your browser cache removes it.</p>
</div>
</section>

<section>
<h2>What each page loads</h2>
<div class="measure">
<p>Every page loads one stylesheet and one small icon, both from this same site. The
study page also loads two chart images, again from here. The tools page loads one
JSON file listing the coordinates and names of the 241 brain regions.</p>
<p>That is the complete list. No fonts from Google, no scripts from a CDN, no
analytics beacon, no embedded video, no iframe, no social widget, no image from
another domain. Nothing on any page causes a request to a server I do not control,
which means no other company learns that you visited.</p>
</div>
</section>

<section>
<h2>The JavaScript that does run</h2>
<div class="measure">
<p>The tools page runs three small scripts, all written for this project and served
from here.</p>
<p>One simulates study designs so you can see how often a study of a given size would
find a given effect. One lets you step through the analysis choices and see the
result each combination gives. One draws the brain map and handles clicking and
filtering.</p>
<p>All three run entirely inside your browser. None of them sends anything anywhere,
and none of them remembers anything after you close the tab. Every number they show
is computed on your own machine from data already delivered with the page. If you
block JavaScript, the study page is completely unaffected and the tools page shows
plain text instead of the interactive parts.</p>
</div>
</section>

<section>
<h2>Check it yourself</h2>
<div class="measure">
<p>You do not have to believe any of this.</p>
<p>Open your browser's developer tools, usually with F12 or Command-Option-I. Go to
the Application tab in Chrome or Edge, or Storage in Firefox and Safari, and look at
Cookies for this domain. It will be empty. Look at Local Storage and Session Storage
in the same panel. Also empty.</p>
<p>Then open the Network tab and reload the page. Every request listed will be to
this domain. If you ever see one that is not, something has gone wrong and I would
like to know about it through the <a href="{REPO}">repository</a>.</p>
<p>There is also an automated test in that repository which scans every built page
for cookie calls, storage calls, analytics scripts and off-site resources. It fails
the build rather than letting this page become untrue.</p>
<p class="small">Last updated {UPDATED}.</p>
</div>
</section>
"""
    write("cookies.html", "Cookies", body,
          "No cookies, no local storage, no service worker and no third-party "
          "requests, with instructions to verify it yourself.")


def build_accessibility() -> None:
    body = f"""
<h1>Accessibility</h1>
<p class="lede">The target is WCAG 2.1 level AA. This page says what has been done,
and is honest about the places where the site still falls short, because an
accessibility statement that only lists successes is not much use to anyone.</p>

<section>
<h2>Structure and navigation</h2>
<div class="measure">
<p>Every page starts with a skip link that jumps straight to the main content, so a
keyboard or screen reader user does not have to walk through the navigation on every
page.</p>
<p>Headings are real headings and run in order without skipping levels, so a screen
reader can jump through the structure and build an outline. The main article is one
long page with a section jump bar, which means fewer navigation steps than the eight
separate pages this site used to have.</p>
<p>Navigation is marked as navigation, the current page is flagged with
<code>aria-current</code>, and every page declares its language. Tables use real
header cells and carry captions describing what they show.</p>
<p>Everything works with a keyboard alone. Focus is visible at all times, with a
two-pixel outline rather than a faint colour shift, and focus order follows reading
order.</p>
</div>
</section>

<section>
<h2>Reading and text</h2>
<div class="measure">
<p>Body text is 19 pixels with a line height of about 1.6 and a measure of roughly 34
rem, which keeps lines at a comfortable length rather than running the full width of a
monitor.</p>
<p>Nothing is sized in fixed pixels in a way that breaks zoom. The page reflows down
to a 320 pixel screen without a horizontal scroll bar. Wide tables scroll inside their
own container rather than pushing the whole page sideways.</p>
<p>Colours were chosen to meet the AA contrast ratio in both the light and dark
themes. The site follows whatever theme your system is set to rather than forcing
one, and it does not override your browser's font size.</p>
</div>
</section>

<section>
<h2>Colour and meaning</h2>
<div class="measure">
<p>Only two colours carry meaning anywhere on the site: one for the right side of the
brain and patients, one for the left side and controls. Everything else is ink on
paper.</p>
<p>Colour is never the only signal. Control models in the results table are labelled
in text as well as shown in grey. The lateralisation figure labels each bar with the
side it belongs to. Every chart states its values in a table or in the surrounding
text.</p>
</div>
</section>

<section>
<h2>Motion</h2>
<div class="measure">
<p>There is no animation, no autoplay, no parallax, no carousel and nothing that
moves on its own. Smooth scrolling for the section links is disabled automatically if
your system asks for reduced motion.</p>
</div>
</section>

<section>
<h2>The interactive tools</h2>
<div class="measure">
<p>These are the hardest parts to make accessible and they are handled differently
from one another.</p>
<p>The replication calculator uses two standard range sliders, which are keyboard
operable by default with arrow keys. Every number it produces is written out as text
next to the chart, and the verdict below it is a plain sentence. You can use the whole
tool without seeing the chart at all.</p>
<p>The pipeline explorer uses standard dropdown menus, which work with a keyboard and
are read correctly by screen readers. Its result is text.</p>
<p>The brain map is a scatter plot of 241 points, which is inherently visual. Each
point can be reached with Tab and activated with Enter or Space, and each has a text
label that a screen reader announces. Network filters are real buttons with pressed
state. Underneath the map, the same information is repeated as a ranked table, so the
content is available without the picture.</p>
</div>
</section>

<section>
<h2>Where this still falls short</h2>
<div class="measure">
<p>Being specific, because vague statements here help nobody:</p>
</div>
<ul class="flaws">
<li><strong>The brain map favours sighted users.</strong> The table underneath carries
the same numbers, but spatial relationships between regions are not conveyed. There is
no audio description and no sonification.</li>
<li><strong>Tabbing through 241 points is tedious.</strong> There is no way to skip
past the map to the table below without going through every region, which is a real
problem I have not fixed.</li>
<li><strong>Region names are compressed atlas labels</strong> such as "R SomMotB S2 2".
They are hard to read aloud and mean little without background knowledge. The full
description appears in the detail panel, but it is still jargon.</li>
<li><strong>Charts are images without long descriptions.</strong> Each has alt text
and a caption, but a genuinely equivalent description of a distribution would be
better.</li>
<li><strong>Not tested with real assistive technology.</strong> The site has been
checked for keyboard operation, heading order, contrast ratios, reflow and zoom. It
has not been tested with JAWS, NVDA, VoiceOver or Dragon by someone who uses them
daily, and that is the test that actually counts.</li>
<li><strong>The subject matter is dense.</strong> Plain wording helps, but this is a
technical write-up about brain imaging statistics and no amount of formatting makes
that easy reading.</li>
</ul>
</section>

<section>
<h2>Tell me what is broken</h2>
<div class="measure">
<p>If something here stops you using the site, open an issue on the
<a href="{REPO}">project repository</a> and describe what happened and what you were
using. That is the fastest route to a fix, and accessibility problems get priority
over new features.</p>
<p class="small">Last updated {UPDATED}. This statement describes the site as built on
that date and is reviewed whenever the pages change.</p>
</div>
</section>
"""
    write("accessibility.html", "Accessibility", body,
          "Targeting WCAG 2.1 AA. What works, how the interactive tools behave, and "
          "six specific places the site still falls short.")
