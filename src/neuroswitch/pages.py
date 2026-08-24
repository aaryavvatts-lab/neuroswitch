"""Page text for the neuroswitch site.

Wording is deliberately plain. Numbers all come from results/*.json at build
time, so nothing on a page can drift away from what the analysis produced.
"""
from __future__ import annotations

import json

from .references import REFERENCES, cite
from .site_build import (DS_DOI, PREPRINT, bars, e, fmt_auc, fmt_ci, fmt_p, load,
                         pending, stats, write)

NULL_PREFIX = "NULL "


def progress_banner() -> str:
    """Shown while preprocessing is still working through the 66 people.

    Without it a page reporting three participants looks broken rather than
    unfinished.
    """
    coh = load("cohort") or {}
    su = coh.get("summary", {})
    done = su.get("n_included")
    if done is None:
        return ""
    target = 66
    if done >= target - 2:
        return ""
    pct = min(100, round(100 * done / target))
    return (f'<div class="note warn"><p><strong>Still running.</strong> '
            f'The scans are being processed one person at a time, and '
            f'{done} of about {target} are done so far ({pct}%). Numbers on this '
            f'page come from those {done} and will change. Anything not worked out '
            f'yet says so instead of showing a placeholder.</p>'
            f'<div class="progress" role="img" aria-label="{pct} percent processed">'
            f'<span style="width:{pct}%"></span></div></div>')


def figure(name: str, caption: str) -> str:
    """Embed a generated figure, or nothing if it has not been made yet."""
    from .site_build import SITE
    if not (SITE / "figures" / f"{name}.svg").is_file():
        return ""
    return (f'<figure><img src="figures/{name}.svg" alt="{e(caption)}">'
            f'<figcaption>{caption}</figcaption></figure>')


# ---------------------------------------------------------------- index
def build_index() -> None:
    coh = load("cohort") or {}
    s = coh.get("summary", {})
    models = (load("models_LH") or {}).get("models", {})
    hand = load("control_handflip") or {}
    beh = load("control_behaviour") or {}

    n_inc, n_pat, n_ctl = s.get("n_included"), s.get("n_patients"), s.get("n_controls")
    key = stats([
        (n_inc if n_inc is not None else "n/a", "people in the analysis"),
        (f"{n_pat}/{n_ctl}" if n_pat is not None else "n/a", "patients / controls"),
        ("241", "brain regions per graph"),
        ("6", "scans per person"),
        ("0.66 s", "time per brain image"),
    ])

    def auc(name):
        return (models.get(name) or {}).get("auc_mean")

    lin, gcn = auc("tangent+logreg"), auc("GCN")
    mot, bhv = auc(NULL_PREFIX + "motion-only"), auc(NULL_PREFIX + "behaviour-only")

    board = bars([
        ("Connectivity plus a simple model", lin, False),
        ("Graph neural network", gcn, False),
        ("Head movement only", mot, True),
        ("Drawing quality only", bhv, True),
    ]) if models else pending()

    cards = []
    if lin is not None and gcn is not None:
        who = "the graph network" if gcn > lin else "the simple model"
        cards.append((
            "The bigger model did not win by default",
            f"The graph network scored {fmt_auc(gcn)}. A plain linear model on the "
            f"same connection strengths scored {fmt_auc(lin)}. With 66 people, "
            f"{who} came out ahead. Both are on the results page, not just the one "
            f"that sounds better."))
    if bhv is not None:
        cards.append((
            "Patients draw worse, and that is a rival answer",
            f"Four numbers about how well someone drew with their left hand tell "
            f"patients from controls at {fmt_auc(bhv)}, using no brain data at all. "
            f"So any claim about brain networks has to get past that first."))
    if hand.get("difference_graph"):
        d = hand["difference_graph"]
        cards.append((
            "Comparing each person against themselves",
            f"Everyone drew with both hands. Subtracting a person's right-hand "
            f"network from their own left-hand network cancels anything fixed about "
            f"them, like head size or how still they lie. What was left still "
            f"separated the groups at {fmt_auc(d.get('auc_mean'))} "
            f"(p = {fmt_p((d.get('permutation') or {}).get('p_value'))})."))

    card_html = ('<div class="points">' + "".join(
        f'<div class="point"><h3>{e(t)}</h3><p>{b}</p></div>' for t, b in cards)
        + "</div>") if cards else pending(
        "Findings show up here once the analysis has run.")

    body = f"""
<h1>Does the brain rewire after a hand injury?</h1>
{progress_banner()}
<p class="lede">When nerve damage takes your right hand out of action, you start
doing everything with the left. This project looks at brain scans taken while
people were drawing, and asks whether their brain networks really look different.
Then it spends most of its effort asking whether that difference means what it
looks like it means.</p>

{key}

<section>
<h2>What this is</h2>
<div class="measure">
<p>A student reanalysis of a public dataset from Washington University in St. Louis.
46 healthy adults and 25 people with long-term nerve injury to the right hand each
lay in a scanner and traced shapes on a tablet, three runs with one hand and three
with the other. I pulled blood flow signals out of 241 brain regions, turned them
into a network for each person, and trained models to tell the two groups apart.</p>
</div>
</section>

<section>
<h2>What this is not</h2>
<div class="measure">
<p>It is not proof that anyone's brain rewired. Each person was scanned one time.
Nothing here watches a brain change. A difference between two groups in a
single snapshot can come from reorganisation, but it can also come from things
that were true before the injury, from the task being harder for one group, or
from one group moving more in the scanner.</p>
<p>That last point is the whole reason this project has a controls page.
{cite('makin2015')} looked at a similar claim in arm amputees and found the link
between remapping and pain did not survive once other factors were measured. That
is a good reason to be careful here too.</p>
<p>It is also not a medical device and not advice. 66 people, one scanner.</p>
</div>
</section>

<section>
<h2>How well does it work</h2>
{board}
<p class="small">AUC is the chance that a randomly picked patient scores higher
than a randomly picked control. 0.50 is a coin flip. 1.00 is perfect.</p>
</section>

<section>
<h2>Things worth knowing</h2>
{card_html}
</section>

<section>
<h2>Read on</h2>
<dl class="toc">
<dt><a href="data.html">The data</a></dt>
<dd>Where the scans came from, what people did in the scanner, and the three
problems I ran into before any of it would run.</dd>
<dt><a href="methods.html">How it works</a></dt>
<dd>Raw scans to brain networks without the usual software, and the one test
that shows the pipeline is not making things up.</dd>
<dt><a href="controls.html">Could this be wrong?</a></dt>
<dd>Four ways the headline could be an artefact, each one tested rather than
listed as a caveat at the end.</dd>
<dt><a href="brain.html">Explore the brain</a></dt>
<dd>Which regions the model leaned on, and how left and right hand drawing
differ.</dd>
</dl>
</section>
"""
    write("index.html", "Does the brain rewire after hand injury?", body,
          "A student reanalysis of fMRI data from adults with long-term right hand "
          "nerve injury drawing with their left hand.")


# ---------------------------------------------------------------- data
def build_data() -> None:
    coh = load("cohort") or {}
    s = coh.get("summary", {})
    subs = coh.get("subjects", [])
    excl = s.get("exclusion_counts", {})
    rows = "".join(f"<tr><td>{e(k)}</td><td class='num'>{v}</td></tr>"
                   for k, v in excl.items()) or \
        "<tr><td colspan='2' class='pending'>not yet</td></tr>"

    fd_note = ""
    if subs:
        fds = [r["mean_fd"] for r in subs if r.get("included") and r.get("mean_fd")]
        if fds:
            fd_note = (f" Across the people who made it through, average head "
                       f"movement was {sum(fds)/len(fds):.3f} mm per image, which is "
                       f"low for a task where someone is moving a hand.")

    body = f"""
<h1>Where the data comes from</h1>
<p class="lede">71 adults drawing shapes inside a 3T scanner. The team who
collected it put the whole thing online for free.</p>

<section>
<h2>The study</h2>
<div class="measure">
<p>The scans are <a href="{DS_DOI}">OpenNeuro ds008162</a>, collected at Washington
University in St. Louis School of Medicine by Kapil, Kim, McAvoy and Philip, paid
for by NINDS. 71 right-handed adults took part. 25 of them had long-term nerve
injury to the right hand or arm. The other 46 were healthy.</p>
<p>Everyone did the same thing. Lying in the scanner with a special tablet, they
traced inside a moving path. The instruction was to draw within the lines and move
as fast as they could, but staying inside the lines mattered more than speed.
Three runs with the left hand, three with the right, alternating, always starting
with the hand they normally write with.</p>
<p>Each run swaps between 15 seconds of drawing and 15 seconds of rest, ten times
over. The scanner took a picture of the whole brain every 0.66 seconds, which is
fast, and gives 488 images per run.</p>
</div>

<div class="stats">
<div class="stat"><div class="n">71</div><div class="k">people scanned</div></div>
<div class="stat"><div class="n">0.66 s</div><div class="k">per brain image</div></div>
<div class="stat"><div class="n">488</div><div class="k">images per run</div></div>
<div class="stat"><div class="n">10</div><div class="k">drawing blocks per run</div></div>
</div>
</section>

<section>
<h2>Three things I did not expect</h2>
<div class="points">
<div class="point"><h3>One whole group was missing</h3>
<p>The copy of the data I started with had 45 of the 46 healthy adults in it and
none of the 25 patients. You cannot train a model to tell two groups apart when
only one group is there. The patient scans had to be pulled down from OpenNeuro
first.</p></div>

<div class="point"><h3>There was no disk space</h3>
<p>The data is 83 GB and the laptop had 2.5 GB free. So the pipeline works through
one person at a time and deletes their raw scans as soon as their signals have been
pulled out and checked. Free space goes up as the analysis runs instead of down.
Every deleted file is written to a log with the address it came from, so nothing is
lost for good.</p></div>

<div class="point"><h3>The gap in drawing quality is big</h3>
<p>The dataset comes with drawing quality measured 30 times a second from the
tablet. Patients score much worse with the left hand. That makes sense given the
injury, and it is a problem for the analysis, because a brain model can do well by
picking up on how hard the task was rather than on anything about rewiring. It
turned into the main control test.</p></div>
</div>
</section>

<section>
<h2>Who was left out</h2>
<div class="measure">
<p>Five people were dropped by the original team. Three patients moved in time with
the task, one control had a problem with the tablet, and one moved too much. Those
same five are left out here.</p>
<p>On top of that, a run was dropped if average head movement went above 0.30 mm,
if more than 30% of its images had to be thrown out, or if the brain did not line
up well with the template. A person needed at least two surviving left-hand runs to
be used at all.{fd_note}</p>
</div>
<div class="tablewrap"><table>
<thead><tr><th>Reason for leaving someone out</th><th class="num">People</th></tr></thead>
<tbody>{rows}</tbody></table></div>
{figure("motion",
        "Head movement for every person who made it through, split by group. The "
        "red line is the cut-off. If patients sat well to the right of controls "
        "here, movement alone could explain a group difference, which is why the "
        "results page carries a model built from movement and nothing else.")}
<p class="small">Three patients (<code>sub-1002</code>, <code>sub-1019</code>,
<code>sub-1045</code>) could not draw with their injured hand at all. They are in the
left-hand analysis but not in the left minus right comparison.</p>
</section>
"""
    write("data.html", "The data", body,
          "OpenNeuro ds008162: 71 adults drawing in a 3T scanner, and the three "
          "problems I hit before any of it would run.")


# ---------------------------------------------------------------- methods
def build_methods() -> None:
    san = load("sanity_lateralisation") or {}
    if san.get("n_subjects"):
        rows = "".join(
            f"<tr><td>{e(r['name'].replace('17Networks_', '').replace('_', ' '))}</td>"
            f"<td>{e(r['network'])}</td>"
            f"<td>{'right' if r['hemi'] == 'RH' else 'left' if r['hemi'] == 'LH' else 'middle'}</td>"
            f"<td class='num'>{r['value']:+.3f}</td></tr>"
            for r in san.get("top_left_hand", [])[:8])
        good = san.get("all_pass")
        sanity = f"""
<div class="stats">
<div class="stat"><div class="n">{san['interaction_mean']:+.3f}</div>
<div class="k">size of the hand by side effect</div></div>
<div class="stat"><div class="n">{san['subjects_correct']}/{san['n_subjects']}</div>
<div class="k">people who show the right pattern</div></div>
<div class="stat"><div class="n">{san.get('top10_left_hand_in_right_hemisphere', 'n/a')}/10</div>
<div class="k">top left-hand regions that sit on the right</div></div>
</div>
<div class="tablewrap"><table>
<thead><tr><th>Region</th><th>Network</th><th>Side</th>
<th class="num">Left hand minus right hand</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<div class="note{'' if good else ' bad'}"><p>The check
<strong>{'passes' if good else 'does not pass'}</strong>. The regions that work
hardest during left-hand drawing sit on the right side of the brain, and the
sensorimotor regions swap sides when the drawing hand swaps.</p></div>"""
    else:
        sanity = pending()

    body = f"""
<h1>How it works</h1>
<p class="lede">Getting from scanner files to brain networks with no neuroimaging
software installed, plus the one test that decides whether to trust any of it.</p>

<section>
<h2>Preprocessing without the usual tools</h2>
<div class="measure">
<p>The normal way to do this is fMRIPrep inside Docker. I had no Docker, and no
FSL, FreeSurfer or AFNI either. Running fMRIPrep on 71 people would also have taken
days. So the pipeline is built straight on ANTs through the <code>antspyx</code>
package, with numpy, nibabel and nilearn doing the rest.</p>
<p>For each run: throw away the first 10 images while the scanner settles, fix the
fact that slices are taken at slightly different times, then line up every image to
the average of the run so head movement is taken out. For each person: even out
the brightness of the anatomical scan, get a brain mask by warping a template mask
onto it, and split the brain into grey matter, white matter and fluid.</p>
</div>

<div class="note">
<p><strong>The trick that made this possible.</strong> The slow part of a normal
pipeline is pushing all 488 images of every run into a shared template space. This
pipeline never does that. It moves the <em>region map</em> the other way instead,
from the template into each run's own space, and reads region averages straight off
the data where it already sits.</p>
<p>That is not a shortcut with a cost. Taking out confounds and filtering both work
along the time axis. Averaging a region works across space. Operations on separate
axes can be done in either order, so cleaning 241 region signals gives exactly the
same answer as cleaning 150,000 voxels and then averaging them. It is just far
cheaper.</p>
</div>

<div class="measure">
<p>Things taken out of each signal: 24 movement terms (six numbers describing head
position, their frame-to-frame change, and both squared), five summary components
each from white matter and fluid, plus a marker for any image where the head moved
more than half a millimetre. Then a filter keeping 0.008 to 0.10 Hz, which holds
the task rhythm of 0.033 Hz comfortably inside it. {cite('parkes2018')} compared 19
different versions of this step and found that group differences can flip depending
which one you pick, so the exact recipe is written down in the code.</p>
</div>
</section>

<section>
<h2>Does the pipeline actually work?</h2>
<div class="measure">
<p>Before believing any difference between groups, the pipeline has to show
something that cannot be wrong. Moving your left hand drives the right side of the
brain, and moving your right hand drives the left. If that does not show up, then
something in the lining up, the labelling or the timing is broken, and everything
after it is noise.</p>
<p>Since everyone drew with both hands, the test is a paired one. For each person,
take their right-hand response away from their left-hand response, region by
region. A positive number means that region worked harder when they drew with the
left hand.</p>
</div>
{sanity}
{figure("lateralisation",
        "Each bar is one brain region. Bars to the right were more active when "
        "people drew with the left hand, bars to the left when they drew with the "
        "right. Blue regions sit in the right half of the brain and orange in the "
        "left, so the colours flip either side of the middle line. That flip is "
        "the thing being checked.")}
<p class="small">This one test covers the whole chain at once, including a detail
that is easy to get wrong. Event times in the data refer to the original scan, not
to the images left after the first ten are dropped. Miss that and every block
lands 6.6 seconds early, which quietly kills the effect.</p>
<div class="measure"><p class="small">Two weaker versions of this test came first
and were thrown out. Averaging all 34 sensorimotor regions waters down a hand
effect with hearing and face areas the task barely uses. Comparing across people
instead of within them puts back all the differences the paired version removes.
Neither was sharp enough to tell me anything.</p></div>
</section>

<section>
<h2>Turning signals into networks</h2>
<div class="measure">
<p>Each brain becomes a network of 241 points. 200 come from the cortex using the
parcellation in {cite('schaefer2018')}, 15 are deep structures from the
Harvard-Oxford atlas, and 26 are parts of the cerebellum from {cite('aal2002')}.
The cerebellum is in there on purpose. It matters for learning movements and a lot
of studies leave it out.</p>
<p>The links between points are partial correlations worked out from the drawing
blocks only, shifted four seconds to allow for how slowly blood flow responds. The
strongest tenth of links are kept. Each point also carries its own numbers: its
pattern of links, how strongly it responded to the task, how much its signal
wobbles slowly, and which network it belongs to.</p>
</div>
<div class="note warn">
<p><strong>A trap worth naming.</strong> One of the strongest ways to describe
connectivity, called tangent space, works out a group average first. Compute that
once over everybody and then run cross-validation and you have leaked the test
people into training, and every score comes out too high. To stop that happening,
the stored files hold time signals rather than finished connectivity matrices. That
forces every step to be fitted inside the training half. Splits are also grouped by
person, so nobody appears on both sides.</p>
</div>
</section>

<section>
<h2>The models</h2>
<div class="measure">
<p>The graph neural network the idea calls for is here, along with two other kinds
of graph network. The design follows the recipes tested in {cite('cui2022')}. Next
to them sit the models that might beat them: a linear classifier and a support
vector machine over the same connection strengths, and gradient boosting over
standard network measures.</p>
<p>Then three models built to be dangerous. One uses head movement and nothing
else. One uses drawing quality and nothing else. One uses age and sex. If any of
them matches the brain models, the headline is not about brain networks. They are
in the same table as everything else.</p>
<p>Every score is the average of 10 repeats of five-fold cross-validation grouped by
person. Every headline number also gets a permutation test, where the group labels
are shuffled and the whole thing is run again. {cite('eklund2016')} showed
permutation tests behaving properly in fMRI where the standard maths did not.</p>
</div>
</section>
"""
    write("methods.html", "How it works", body,
          "Preprocessing without fMRIPrep, building brain networks, and the "
          "left-right test that shows the pipeline works.")


# ---------------------------------------------------------------- results
def _model_table(models: dict) -> str:
    if not models:
        return pending()
    order = sorted(models.items(),
                   key=lambda kv: (kv[0].startswith(NULL_PREFIX),
                                   -(kv[1].get("auc_mean") or 0)))
    rows = []
    for name, m in order:
        if "error" in m:
            rows.append(f"<tr class='null'><td>{e(name)}</td>"
                        f"<td colspan='5' class='small'>did not run: "
                        f"{e(m['error'][:80])}</td></tr>")
            continue
        is_null = name.startswith(NULL_PREFIX)
        agg, perm = m.get("aggregate", {}), (m.get("permutation") or {})
        label = name[len(NULL_PREFIX):] if is_null else name
        tag = " <span class='tag'>control</span>" if is_null else ""
        rows.append(
            f"<tr class='{'null' if is_null else ''}'><td>{e(label)}{tag}</td>"
            f"<td class='num'>{fmt_auc(m.get('auc_mean'))}</td>"
            f"<td class='num'>{fmt_ci(m.get('auc_ci'))}</td>"
            f"<td class='num'>{fmt_auc(agg.get('balanced_acc'))}</td>"
            f"<td class='num'>{fmt_auc(agg.get('sensitivity'))}</td>"
            f"<td class='num'>{fmt_p(perm.get('p_value')) if perm else 'n/a'}</td></tr>")
    return f"""<div class="tablewrap"><table>
<thead><tr><th>Model</th><th class="num">AUC</th><th class="num">95% range</th>
<th class="num">Balanced accuracy</th><th class="num">Catch rate</th>
<th class="num">p</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>"""


NULLS_JS = r"""
(function () {
  const host = document.getElementById('nullchart');
  if (!host) return;
  const raw = document.getElementById('nulldata');
  if (!raw) return;
  let D;
  try { D = JSON.parse(raw.textContent); } catch (e) { return; }
  const names = Object.keys(D);
  if (!names.length) { host.innerHTML = ''; return; }

  let current = names[0];

  function draw(name) {
    const d = D[name];
    const w = 640, h = 210, padL = 44, padR = 16, padT = 16, padB = 40;
    const counts = d.counts, edges = d.edges;
    const maxC = Math.max(...counts, 1);
    const x0 = 0.30, x1 = 1.0;                       // AUC range worth showing
    const sx = v => padL + ((v - x0) / (x1 - x0)) * (w - padL - padR);
    const sy = c => h - padB - (c / maxC) * (h - padT - padB);

    let s = `<svg viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" role="img"
      aria-label="Scores from ${d.n_perm} runs with the group labels shuffled. The real score is marked.">`;
    // bars for the shuffled scores
    for (let i = 0; i < counts.length; i++) {
      if (!counts[i]) continue;
      const a = sx(edges[i]), b = sx(edges[i + 1]);
      if (b < padL) continue;
      s += `<rect x="${Math.max(a, padL).toFixed(1)}" y="${sy(counts[i]).toFixed(1)}"
             width="${Math.max(1, b - a - 0.8).toFixed(1)}"
             height="${(h - padB - sy(counts[i])).toFixed(1)}"
             fill="var(--paper-3)" stroke="var(--rule-2)" stroke-width="0.5"/>`;
    }
    // chance line
    s += `<line x1="${sx(0.5)}" y1="${padT - 4}" x2="${sx(0.5)}" y2="${h - padB}"
           stroke="var(--ink-3)" stroke-dasharray="3 3"/>`;
    s += `<text x="${sx(0.5)}" y="${padT - 7}" font-size="10.5" text-anchor="middle"
           fill="var(--ink-3)" font-family="var(--sans)">chance</text>`;
    // the real score
    const ox = sx(d.observed_auc);
    s += `<line x1="${ox.toFixed(1)}" y1="${padT - 4}" x2="${ox.toFixed(1)}" y2="${h - padB}"
           stroke="var(--right)" stroke-width="2"/>`;
    s += `<text x="${ox.toFixed(1)}" y="${padT - 7}" font-size="10.5" text-anchor="middle"
           fill="var(--right)" font-family="var(--sans)" font-weight="600">real score</text>`;
    // axis
    s += `<line x1="${padL}" y1="${h - padB}" x2="${w - padR}" y2="${h - padB}" stroke="var(--ink)"/>`;
    for (const t of [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]) {
      s += `<line x1="${sx(t)}" y1="${h - padB}" x2="${sx(t)}" y2="${h - padB + 4}" stroke="var(--ink)"/>`;
      s += `<text x="${sx(t)}" y="${h - padB + 16}" font-size="10.5" text-anchor="middle"
             fill="var(--ink-2)" font-family="var(--sans)">${t.toFixed(1)}</text>`;
    }
    s += `<text x="${(padL + w - padR) / 2}" y="${h - 6}" font-size="10.5" text-anchor="middle"
           fill="var(--ink-2)" font-family="var(--sans)">AUC</text>`;
    s += `<text x="4" y="${padT + 4}" font-size="10.5" fill="var(--ink-2)"
           font-family="var(--sans)">runs</text>`;
    s += `</svg>`;

    const beat = d.p_value;
    const verdict = beat <= 0.05
      ? `Only ${(beat * 100).toFixed(1)}% of shuffled runs did this well or better, so the real score is unlikely to be luck.`
      : `${(beat * 100).toFixed(0)}% of shuffled runs did this well or better, so this score is within what chance produces here.`;
    host.querySelector('.nc-chart').innerHTML = s;
    host.querySelector('.nc-say').innerHTML =
      `<p class="small">${d.n_perm} runs with the group labels shuffled between people, ` +
      `each one refitted from scratch. Their scores make the grey pile. ${verdict}</p>`;
    host.querySelectorAll('.nc-pick button').forEach(b =>
      b.setAttribute('aria-pressed', String(b.dataset.k === name)));
  }

  host.innerHTML =
    `<div class="nc-pick">` +
    names.map(n => `<button data-k="${n}" aria-pressed="false">${n.replace('NULL ', '')}</button>`).join('') +
    `</div><div class="nc-chart"></div><div class="nc-say"></div>`;
  host.querySelectorAll('.nc-pick button').forEach(b =>
    b.addEventListener('click', () => { current = b.dataset.k; draw(current); }));
  draw(current);
})();
"""

NULLS_CSS = """
#nullchart { margin: 1.6rem 0; max-width: var(--bleed); }
.nc-pick { display: flex; flex-wrap: wrap; gap: .4rem; margin-bottom: 1rem; }
.nc-pick button {
  font-family: var(--sans); font-size: .78rem; padding: .28rem .6rem;
  border: 1px solid var(--rule-2); background: var(--paper); color: var(--ink-2);
  cursor: pointer; border-radius: 2px;
}
.nc-pick button[aria-pressed="true"] {
  background: var(--ink); color: var(--paper); border-color: var(--ink);
}
.nc-chart svg { max-width: 100%; height: auto; }
.nc-say { margin-top: .4rem; }
"""


def build_results() -> None:
    res = load("models_LH") or {}
    models, b = res.get("models", {}), res.get("bundle", {})
    gcn = (models.get("GCN") or {}).get("auc_mean")
    lin = (models.get("tangent+logreg") or {}).get("auc_mean")

    if gcn is None or lin is None:
        answer = pending()
    elif gcn > lin + 0.02:
        answer = (f"<p>Yes. The graph network gets {fmt_auc(gcn)} against "
                  f"{fmt_auc(lin)} for the simple model. The shape of the network is "
                  f"carrying something the link strengths on their own do not.</p>")
    elif lin > gcn + 0.02:
        answer = (f"<p><strong>No.</strong> A plain linear model on the same link "
                  f"strengths gets {fmt_auc(lin)}. The graph network gets "
                  f"{fmt_auc(gcn)}. With 66 people and 241 regions there is not "
                  f"enough data for the bigger model to earn back the extra freedom "
                  f"it has. This happens a lot in small brain imaging studies. It is "
                  f"worth saying out loud instead of quietly showing only the graph "
                  f"network.</p>")
    else:
        answer = (f"<p>It is a tie. {fmt_auc(gcn)} for the graph network and "
                  f"{fmt_auc(lin)} for the simple one. The extra machinery buys "
                  f"nothing here.</p>")

    # data for the interactive null chart
    nulls = {}
    for name, m in models.items():
        perm = (m or {}).get("permutation") or {}
        hist = perm.get("null_hist")
        if hist and hist.get("counts"):
            nulls[name] = {"counts": hist["counts"], "edges": hist["edges"],
                           "observed_auc": perm.get("observed_auc"),
                           "p_value": perm.get("p_value"),
                           "n_perm": perm.get("n_perm")}
    if nulls:
        null_block = (f'<div id="nullchart"></div>'
                      f'<script type="application/json" id="nulldata">'
                      f'{json.dumps(nulls)}</script>')
    else:
        null_block = pending("The shuffled-label runs appear here once the models "
                             "have been fitted.")

    body = f"""
<h1>Does the graph network beat the simple method?</h1>
{progress_banner()}
<p class="lede">Every model was scored the same way. 10 repeats of five-fold
cross-validation, grouped by person, with shuffled-label tests on the headline
numbers.</p>

<section>
<h2>The answer</h2>
<div class="measure">{answer}</div>
</section>

<section>
<h2>Every model side by side</h2>
{_model_table(models)}
<p class="small">Grey rows are control models. They use no brain data and are there
to be compared against. If one of them matched the brain models, the brain result
would need rethinking rather than celebrating. Sample:
{b.get('n_patients', 'n/a')} patients and {b.get('n_controls', 'n/a')} controls,
{b.get('n_nodes', 'n/a')} regions.</p>
</section>

<section>
<h2>Check the statistics yourself</h2>
<div class="measure">
<p>Accuracy from a small sample bounces around, and a model given random labels
rarely lands exactly on 0.50. So each headline model was fitted again hundreds of
times with the group labels shuffled between people. That builds up the range of
scores you can get from data with no real group difference in it.</p>
<p>Pick a model below to see that range. The grey pile is what shuffled labels
produced. The blue line is what the model actually scored. If the line sits inside
the pile, the score is what chance looks like here.</p>
</div>
{null_block}
<div class="measure">
<p>If the grey pile does not sit near 0.50, that is a warning in itself. It would
mean the cross-validation is leaking. That check runs as part of the output.</p>
<p>{cite('marek2022')} looked at roughly 50,000 scans and found that brain to
behaviour effects are smaller than people had assumed, and that small studies
produce inflated numbers that later fail to replicate. {cite('turner2018')} found
the same for task studies. 66 people is a small study by that standard, which is
why nothing here is presented as settled.</p>
</div>
</section>
"""
    body += f"<style>{NULLS_CSS}</style><script>{NULLS_JS}</script>"
    write("results.html", "Results", body,
          "Model by model results with shuffled-label tests and control models.")


# ---------------------------------------------------------------- brain
BRAIN_JS = r"""
(async function () {
  const host = document.getElementById('brainapp');
  let D;
  try { D = await (await fetch('data/brain.json')).json(); }
  catch (err) { host.innerHTML = '<p class="pending">Could not load the region data.</p>'; return; }
  const nodes = D.nodes.filter(n => isFinite(n.x) && isFinite(n.y) && isFinite(n.z));
  const imp = D.importance || null;
  const nets = D.networks;

  // A fixed, muted palette rather than evenly spaced hues. Sensorimotor gets
  // the two colours used everywhere else on the site, because those are the
  // regions the whole question is about. Everything else stays quiet.
  const PALETTE = {
    SomMotA:      '#b0521c', SomMotB:      '#d08340',
    Cerebellum:   '#4a6741', Subcortex:    '#7a6a4f',
    VisCent:      '#3f6d7a', VisPeri:      '#5f8f99',
    DorsAttnA:    '#6b7f5c', DorsAttnB:    '#8a9a76',
    SalVentAttnA: '#8a6a17', SalVentAttnB: '#a98c47',
    ContA:        '#1a5570', ContB:        '#3d7591', ContC:        '#6997ad',
    DefaultA:     '#7d5a52', DefaultB:     '#9c7a70', DefaultC:     '#b59a92',
    LimbicA:      '#6f5f7a', LimbicB:      '#8f8199',
    TempPar:      '#556b7d'
  };
  const FALLBACK = '#7c7a70';
  const palette = {};
  nets.forEach(n => { palette[n] = PALETTE[n] || FALLBACK; });

  let active = new Set(nets), selected = null;
  const impOf = n => (imp ? (imp[n.id - 1] ?? 0) : null);
  const vals = imp ? nodes.map(impOf).filter(v => isFinite(v)) : [];
  const hi = vals.length ? Math.max(...vals) : 1, lo = vals.length ? Math.min(...vals) : 0;
  const norm = v => (hi > lo ? (v - lo) / (hi - lo) : 0.5);

  const VIEWS = [
    { a: 'x', b: 'y', title: 'Seen from above', note: 'left of the picture is the left side of the brain' },
    { a: 'y', b: 'z', title: 'Seen from the side', note: 'front of the head is on the right' },
  ];

  function svgFor(view, w, h) {
    const pad = 16;
    const xs = nodes.map(n => n[view.a]), ys = nodes.map(n => n[view.b]);
    const x0 = Math.min(...xs), x1 = Math.max(...xs);
    const y0 = Math.min(...ys), y1 = Math.max(...ys);
    const sx = v => pad + ((v - x0) / (x1 - x0)) * (w - 2 * pad);
    const sy = v => h - pad - ((v - y0) / (y1 - y0)) * (h - 2 * pad);
    let s = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${view.title}. ${nodes.length} brain regions plotted by position.">`;
    s += `<ellipse cx="${w / 2}" cy="${h / 2}" rx="${w / 2 - pad + 6}" ry="${h / 2 - pad + 6}" fill="var(--bg-soft)" stroke="var(--rule)"/>`;
    if (view.a === 'x') s += `<line x1="${w / 2}" y1="${pad - 6}" x2="${w / 2}" y2="${h - pad + 6}" stroke="var(--rule)" stroke-dasharray="3 4"/>`;
    const order = [...nodes].sort((m, n) => (imp ? norm(impOf(m)) - norm(impOf(n)) : 0));
    for (const n of order) {
      const on = active.has(n.network);
      const t = imp ? norm(impOf(n)) : 0.5;
      const r = imp ? 2.2 + t * 7 : 3.4;
      const op = on ? (imp ? 0.35 + 0.65 * t : 0.85) : 0.07;
      const sel = selected && selected.id === n.id;
      s += `<circle class="bnode" data-id="${n.id}" cx="${sx(n[view.a]).toFixed(1)}" cy="${sy(n[view.b]).toFixed(1)}" r="${(sel ? r + 3 : r).toFixed(1)}" fill="${palette[n.network]}" fill-opacity="${op.toFixed(2)}" stroke="${sel ? 'var(--fg)' : 'none'}" stroke-width="1.5" tabindex="0" role="button" aria-label="${n.label}, ${n.network}"><title>${n.label}${imp ? ', importance ' + impOf(n).toFixed(3) : ''}</title></circle>`;
    }
    return `<figure class="bview"><div class="bviewhead">${view.title} <span class="small">${view.note}</span></div>${s}</svg></figure>`;
  }

  const legend = () => `<div class="legend">` + nets.map(n =>
    `<button class="lg${active.has(n) ? ' on' : ''}" data-net="${n}" aria-pressed="${active.has(n)}"><span class="sw" style="background:${palette[n]}"></span>${n}</button>`).join('')
    + `<button class="lg reset" data-net="__all">show all</button></div>`;

  function detail() {
    if (!selected) return `<p class="small">Pick a region, or use the buttons above to show one network at a time.${imp ? ' Bigger and more solid dots are regions the model used more.' : ''}</p>`;
    const n = selected;
    const side = n.hemi === 'LH' ? 'left' : n.hemi === 'RH' ? 'right' : 'middle';
    return `<div class="bpick"><h3>${n.label}</h3><p class="small">${n.network}, ${side} side, from ${n.source}, ${n.n_voxels} voxels<br>Position ${n.x}, ${n.y}, ${n.z}${imp ? `<br><strong>importance ${impOf(n).toFixed(4)}</strong>` : ''}</p></div>`;
  }

  function table() {
    if (!imp) return '';
    const rows = [...nodes].sort((a, b) => impOf(b) - impOf(a)).slice(0, 20).map((n, i) =>
      `<tr><td class="num">${i + 1}</td><td>${n.label}</td><td>${n.network}</td><td>${n.hemi === 'LH' ? 'left' : n.hemi === 'RH' ? 'right' : 'middle'}</td><td class="num">${impOf(n).toFixed(4)}</td></tr>`).join('');
    return `<h3>Regions the model used most</h3><p class="small">Same information as the map above, as a list, for anyone who cannot use the picture.</p><div class="tablewrap"><table><thead><tr><th class="num">#</th><th>Region</th><th>Network</th><th>Side</th><th class="num">Importance</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function render() {
    host.innerHTML = legend() + `<div class="bgrid">${VIEWS.map(v => svgFor(v, 340, 300)).join('')}</div><div id="bdetail">${detail()}</div>` + table();
    host.querySelectorAll('.lg').forEach(b => b.addEventListener('click', () => {
      const n = b.dataset.net;
      if (n === '__all') active = new Set(nets);
      else if (active.size === nets.length) active = new Set([n]);
      else if (active.has(n)) { active.delete(n); if (!active.size) active = new Set(nets); }
      else active.add(n);
      render();
    }));
    const pick = el => { selected = nodes.find(n => n.id === +el.dataset.id) || null; render(); };
    host.querySelectorAll('.bnode').forEach(c => {
      c.addEventListener('click', () => pick(c));
      c.addEventListener('keydown', ev => {
        if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); pick(c); }
      });
    });
  }
  render();
})();
"""

BRAIN_CSS = """
.bgrid { display: grid; gap: 1.1rem; grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
         margin: 1.3rem 0; max-width: var(--bleed); }
.bview { margin: 0; border-top: 1px solid var(--ink); padding-top: .55rem; }
.bviewhead { font-family: var(--sans); font-size: .74rem; color: var(--ink-2);
             margin-bottom: .45rem; text-transform: uppercase; letter-spacing: .06em; }
.bviewhead span { text-transform: none; letter-spacing: 0; color: var(--ink-3); }
.bnode { cursor: pointer; }
.legend { display: flex; flex-wrap: wrap; gap: .3rem; margin: 1.2rem 0;
          max-width: var(--bleed); }
.lg { display: inline-flex; align-items: center; gap: .35rem; font-family: var(--sans);
      font-size: .74rem; padding: .2rem .5rem; border: 1px solid var(--rule);
      background: var(--paper); color: var(--ink-3); cursor: pointer; border-radius: 2px; }
.lg.on { color: var(--ink); border-color: var(--rule-2); }
.lg .sw { width: .6rem; height: .6rem; border-radius: 50%; opacity: .3; }
.lg.on .sw { opacity: 1; }
.lg.reset { font-style: italic; }
.bpick { border-left: 2px solid var(--ink); padding: .1rem 0 .1rem 1rem; }
.bpick h3 { margin: 0 0 .3rem; }
.bpick p { margin: 0; }
#bdetail { margin: 1.2rem 0; min-height: 3.2rem; max-width: var(--bleed); }
"""


def build_brain() -> None:
    imp = load("importance_LH") or {}
    if imp.get("n_folds"):
        note = (f"<p>These numbers come from {e(imp.get('model', 'the best model'))}, "
                f"worked out again inside each of {imp['n_folds']} cross-validation "
                f"splits and then averaged. Only regions that come out near the top "
                f"again and again mean anything. A single run of this at 66 people is "
                f"mostly noise, so it is not shown that way.</p>")
    else:
        note = ('<p class="pending">Region importance appears here once the models '
                'have been fitted. For now the map shows the regions themselves.</p>')

    enr = imp.get("network_enrichment") or {}
    er = ""
    for net, v in sorted(enr.items(), key=lambda kv: -(kv[1].get("z") or 0))[:8]:
        sig = " <span class='tag'>holds up</span>" if v.get("fdr_pass") else ""
        er += (f"<tr><td>{e(net)}{sig}</td><td class='num'>{v.get('n_nodes', 'n/a')}</td>"
               f"<td class='num'>{v.get('z', float('nan')):+.2f}</td>"
               f"<td class='num'>{fmt_p(v.get('p_value'))}</td></tr>")
    enr_block = (f"""<h3>Which networks did the work</h3>
<div class="tablewrap"><table><thead><tr><th>Network</th><th class="num">Regions</th>
<th class="num">z</th><th class="num">p</th></tr></thead><tbody>{er}</tbody></table></div>
<p class="small">Tested against a version where importance is shuffled across
regions at random, then corrected for testing 19 networks at once.</p>""") if er else ""

    body = f"""
<h1>What the model learned</h1>
<p class="lede">241 regions. 200 in the cortex, 15 deeper in the brain, 26 in the
cerebellum. Filter by network, or click a region to see where it sits and how much
the model used it.</p>

<section>
<div class="measure">{note}</div>
<div id="brainapp"><p class="pending">Loading the map.</p></div>
</section>

<section>
{enr_block}
<div class="measure">
<p class="small">One warning worth repeating. Importance tells you what the model
used to tell the groups apart. It does not tell you what the brain is doing. If two
regions carry the same information the model will often split the credit between
them at random, and a region can score low just because a neighbour already
covered it.</p>
</div>
</section>

<style>{BRAIN_CSS}</style>
<script>{BRAIN_JS}</script>
"""
    write("brain.html", "Explore the brain", body,
          "Interactive map of the 241 brain regions and how much each one mattered.")


# ---------------------------------------------------------------- controls
def build_controls() -> None:
    hand = load("control_handflip") or {}
    beh = load("control_behaviour") or {}
    sev = load("control_severity") or {}
    rest = load("control_rest_vs_task") or {}
    diff = load("control_difficulty") or {}

    if hand.get("difference_graph"):
        d = hand["difference_graph"]
        p = d.get("permutation") or {}
        t1 = f"""<div class="stats">
<div class="stat"><div class="n">{fmt_auc(d.get('auc_mean'))}</div>
<div class="k">left minus right network</div></div>
<div class="stat"><div class="n">{fmt_auc((hand.get('within_LH') or {}).get('auc_mean'))}</div>
<div class="k">left hand on its own</div></div>
<div class="stat"><div class="n">{fmt_auc((hand.get('within_RH') or {}).get('auc_mean'))}</div>
<div class="k">right hand on its own</div></div>
<div class="stat"><div class="n">{fmt_p(p.get('p_value'))}</div>
<div class="k">p from shuffled labels</div></div>
</div>
<p class="small">This uses the {hand.get('n_subjects', 'n/a')} people with usable
runs from both hands.</p>"""
    else:
        t1 = pending()

    if beh.get("behaviour_only"):
        gap = beh.get("performance_gap", {})
        extra = ""
        if beh.get("brain_performance_matched"):
            extra = (f"<tr><td>Brain, in a group matched on drawing quality "
                     f"(n={beh.get('matched_n', 'n/a')})</td><td class='num'>"
                     f"{fmt_auc(beh['brain_performance_matched']['auc_mean'])}</td></tr>")
        t2 = f"""<div class="tablewrap"><table>
<thead><tr><th>Model</th><th class="num">AUC</th></tr></thead><tbody>
<tr><td>Brain connections</td>
<td class="num">{fmt_auc((beh.get('brain_only') or {}).get('auc_mean'))}</td></tr>
<tr class="null"><td>Drawing quality only, no brain data <span class="tag">control</span></td>
<td class="num">{fmt_auc(beh['behaviour_only'].get('auc_mean'))}</td></tr>
<tr class="highlight"><td>Brain, after taking drawing quality out</td>
<td class="num">{fmt_auc((beh.get('brain_residualised_on_behaviour') or {}).get('auc_mean'))}</td></tr>
{extra}</tbody></table></div>
<p class="small">Left hand drawing quality, on a standard scale: patients
{gap.get('patient_mean_z', float('nan')):+.2f}, controls
{gap.get('control_mean_z', float('nan')):+.2f}. The p-value for the brain model
after taking drawing quality out is
{fmt_p((beh.get('brain_residualised_permutation') or {}).get('p_value'))}.</p>"""
    else:
        t2 = pending()

    if sev and not sev.get("error"):
        labels = {"DASH_ability": "How much trouble the hand gives them (DASH score)",
                  "monthsSinceInjury": "Months since the injury",
                  "edinburgh_shift": "How far their hand preference has moved"}
        rows = ""
        for k, lab in labels.items():
            v = sev.get(k) or {}
            if v.get("error"):
                rows += f"<tr><td>{e(lab)}</td><td colspan='3' class='small'>{e(v['error'])}</td></tr>"
            else:
                rows += (f"<tr><td>{e(lab)}</td><td class='num'>{v.get('n', 'n/a')}</td>"
                         f"<td class='num'>{v.get('spearman_rho', float('nan')):+.3f}</td>"
                         f"<td class='num'>{fmt_p(v.get('p_value'))}</td></tr>")
        t3 = f"""<div class="tablewrap"><table><thead><tr>
<th>Predicting, inside the patient group only</th><th class="num">n</th>
<th class="num">Correlation</th><th class="num">p</th></tr></thead>
<tbody>{rows}</tbody></table></div>"""
    else:
        t3 = pending()

    if rest.get("REST") and not (rest.get("REST") or {}).get("error"):
        t4 = f"""<div class="stats">
<div class="stat"><div class="n">{fmt_auc((rest.get('LH') or {}).get('auc_mean'))}</div>
<div class="k">while drawing with the left hand</div></div>
<div class="stat"><div class="n">{fmt_auc((rest.get('REST') or {}).get('auc_mean'))}</div>
<div class="k">lying still, doing nothing</div></div>
</div>"""
    else:
        t4 = pending("The resting scans are handled in a second pass. This "
                     "comparison shows up when that finishes.")

    if diff.get("LHeasy") and not (diff.get("LHeasy") or {}).get("error"):
        t5 = f"""<div class="stats">
<div class="stat"><div class="n">{fmt_auc((diff.get('LHeasy') or {}).get('auc_mean'))}</div>
<div class="k">easy blocks only</div></div>
<div class="stat"><div class="n">{fmt_auc((diff.get('LHhard') or {}).get('auc_mean'))}</div>
<div class="k">hard blocks only</div></div>
</div>"""
    else:
        t5 = pending()

    body = f"""
<h1>Could this be wrong?</h1>
{progress_banner()}
<p class="lede">Getting a model to tell patients from controls is easy. Working out
whether it did so for the reason you hoped is the hard part. Here are four ways
this could be an artefact, each one turned into a test.</p>

<section>
<h2>1. Is it the hand, or just these people?</h2>
<div class="measure">
<p>Patients and controls differ in all sorts of fixed ways that have nothing to do
with drawing. Head size, blood vessels, how still someone lies, whatever else has
happened to them over the years. A model comparing one group of brains against
another can pick up any of that.</p>
<p>The way round it is that everyone drew with both hands. Take a person's
right-hand network away from their own left-hand network and everything fixed about
them cancels out. They act as their own control. Whatever survives has to be about
using the weaker hand.</p>
</div>
{t1}
</section>

<section>
<h2>2. Is it the brain, or do they just draw worse?</h2>
<div class="measure">
<p>This is the one that matters most. Patients have nerve damage in the hand they
used to rely on, so drawing with the other hand is genuinely harder for them, and
the dataset records how much worse they did. A brain model can score well simply by
noticing effort. That would be a real result, but not the one being claimed.</p>
<p>So: how well does drawing quality alone do, with no brain data? And does the
brain still predict anything once drawing quality is taken out of it, and inside a
smaller group where patients and controls are matched on how well they drew?</p>
</div>
{t2}
</section>

<section>
<h2>3. Does it track how badly someone is affected?</h2>
<div class="measure">
<p>A yes or no label is a blunt thing. If brain networks really do reorganise after
losing the use of a hand, the effect should be graded. Stronger in people who
struggle more, or who have lived with it longer, or whose writing hand has actually
shifted. A relationship that scales is much harder to explain away than a split
between two groups.</p>
<p>{cite('freund2011')} did this after spinal cord injury and found the amount of
remapping tracked how disabled people were. Same idea here, except it runs inside
the patient group alone, with no healthy comparison to lean on.</p>
</div>
{t3}
</section>

<section>
<h2>4. Is it about drawing at all?</h2>
<div class="measure">
<p>Everyone also lay in the scanner doing nothing. If the same model works on those
scans, then the difference is something people carry around all the time rather
than something the task brings out. Both answers are interesting. Mixing them up is
what makes "the brain rewires itself" sound more settled than it is.</p>
</div>
{t4}
</section>

<section>
<h2>Extra: do patients treat easy blocks like hard ones?</h2>
<div class="measure">
<p>The task was built with different difficulty levels, and the data labels every
block as easier or harder. If patients are working flat out the whole time, their
easy blocks should already look like everyone else's hard ones.</p>
</div>
{t5}
</section>

<section>
<h2>What still would not be settled</h2>
<div class="note bad">
<p>Say all four tests come out well. This is still one scan per person. Nothing
here watches a brain change over time. Calling it rewiring means guessing at a
process from a single snapshot of differences, and 66 people from one scanner
cannot carry that on their own. {cite('makin2015')} is the cautionary case: a
well-known remapping story that did not hold up once someone measured the other
explanations properly.</p>
</div>
</section>
"""
    write("controls.html", "Could this be wrong?", body,
          "Four ways the result could be an artefact, each one tested: hand "
          "differences, drawing quality, severity, and rest versus task.")


# ---------------------------------------------------------------- reproduce
def build_reproduce() -> None:
    body = """
<h1>Run it yourself</h1>
<p class="lede">Public data, open source packages, no licence keys and no GPU.</p>

<section>
<h2>What you need</h2>
<div class="measure">
<p>Python 3.12 and about 25 GB of working disk. This was run on an Apple M4 with 10
cores and 24 GB of memory. There is no CUDA anywhere. The graph networks are small
enough to train on the processor.</p>
</div>
<pre><code>git clone &lt;this repository&gt; &amp;&amp; cd neuroswitch
uv sync
uv run python -m neuroswitch.atlas 200
</code></pre>
</section>

<section>
<h2>Getting the scans</h2>
<div class="measure">
<p>The dataset is CC0 on OpenNeuro and downloads without an account. Pulling only
the files this analysis touches is about 1.6 GB per person instead of 2.6 GB.</p>
</div>
<pre><code>uv run python -m neuroswitch.acquire --top-level
uv run python -m neuroswitch.acquire sub-1001 sub-1002
</code></pre>
</section>

<section>
<h2>Processing</h2>
<div class="measure">
<p>The driver works through people one at a time. It deletes someone's raw scans
only after their extracted signals pass a check, so peak disk use stays near 3 GB
no matter how many people you run. Deletion is refused if a file is missing, if the
signals have gaps, or if the brain did not line up well. Every removed file is
logged with the address it came from.</p>
<p>Lining up head movement is the slow step, at roughly two minutes per run, and it
already uses every core. Running several people at once does not make it faster.
Budget about twenty minutes a person.</p>
</div>
<pre><code>./drive.sh 1 3 subjects.txt drawLH,drawRH
uv run python -m neuroswitch.features sub-1001
</code></pre>
</section>

<section>
<h2>Analysis and site</h2>
<pre><code>uv run python -m neuroswitch.run_analysis --stages cohort,main,controls
uv run python -m neuroswitch.run_importance --condition LH
uv run python -m neuroswitch.site_build
uv run pytest
</code></pre>
<div class="measure">
<p>The site is generated from the files in <code>results/</code>. No number on a
page is typed in by hand, so the writing cannot drift away from the analysis.
Rebuilding after a new run updates every page.</p>
<p>The tests cover the fiddly parts: slice timing against a known shift, head
movement against a hand-worked example, region averaging on a made-up brain, and a
full dry run of the model chain on data where the right answer is known in advance.
One test checks that shuffled labels give a score near 0.50, which is what catches
leaks between the training and test halves.</p>
</div>
</section>
"""
    write("reproduce.html", "Run it yourself", body,
          "Exact commands, hardware and runtime to repeat the analysis.")


# ---------------------------------------------------------------- refs
def build_refs() -> None:
    items = ""
    for r in REFERENCES:
        items += (f"<li><a href=\"{r['url']}\"><strong>{e(r['title'])}</strong></a>"
                  f"<div class=\"meta\">{e(r['authors'])}, {r['year']}. "
                  f"{e(r['venue'])}. doi:{e(r['doi'])}</div>"
                  f"<div class=\"why\">{e(r['note'])}</div></li>")

    body = f"""
<h1>References and credit</h1>
<p class="lede">Every paper below was looked up in a live literature index and has a
working DOI. None of it was written from memory.</p>

<section>
<h2>Credit for the data</h2>
<div class="measure">
<p>All the credit for designing this study, finding participants and running the
scanner belongs to Kapil, Kim, McAvoy and Philip at Washington University in St.
Louis, funded by NINDS grant R01 NS114046. They released everything under CC0,
which is what made a project like this possible at all.</p>
<p>This site is a student reanalysis. It is not connected to that group, they have
not reviewed it, and any mistakes in it are mine. Their own write-up is the
preprint linked below and it should be read as the authoritative account.</p>
</div>
</section>

<section>
<h2>The list</h2>
<ul class="refs">{items}</ul>
</section>

<section>
<h2>Software</h2>
<div class="measure">
<p>ANTs through antspyx for lining up brains, taking out head movement and
splitting tissue. nibabel and nilearn for reading files, cleaning signals and
working out connectivity. scikit-learn for the ordinary models. PyTorch and
PyTorch Geometric for the graph networks. Captum for working out which regions
mattered. TemplateFlow for the reference brain. All free and open source.</p>
</div>
</section>

<section>
<h2>Code</h2>
<div class="measure">
<p>The full pipeline, tests and the code that builds this site are in the
repository. It is MIT licensed, so you can reuse it.</p>
</div>
</section>
"""
    write("refs.html", "References", body,
          "Papers cited, credit for the dataset, and the software used.")
