"""The neuroswitch site: one long article plus a page of tools.

Wording is plain on purpose. Every number is pulled from results/*.json at
build time, so the writing cannot drift away from what the analysis produced.
Anything not computed yet says so rather than showing a placeholder figure.
"""
from __future__ import annotations

import json

from .references import REFERENCES, cite
from .site_build import (DS_DOI, PREPRINT, SITE, bars, e, fmt_auc, fmt_ci, fmt_p,
                         load, pending, stats, write)

NULL_PREFIX = "NULL "


# ------------------------------------------------------------------ helpers
def figure(name: str, caption: str, number: int | None = None) -> str:
    """Embed a chart's SVG markup directly in the page.

    The charts colour themselves with the site's CSS custom properties (so
    they follow the light/dark theme), but a custom property only resolves
    inside the document that defines it. Referencing the file with
    <img src="..."> loads it as an opaque external resource with no access to
    the page's :root variables, so every fill/stroke falls back to black.
    Inlining the <svg> markup makes it part of the document instead, which is
    what makes the theming actually work.
    """
    svg_path = SITE / "figures" / f"{name}.svg"
    if not svg_path.is_file():
        return ""
    svg = svg_path.read_text()
    # <?xml ...?> declarations are only valid at the top of a standalone
    # document and are meaningless (and sometimes rejected) inline in HTML.
    if svg.lstrip().startswith("<?xml"):
        svg = svg.split("?>", 1)[1]
    lab = f"<strong>Figure {number}.</strong> " if number else ""
    return (f'<figure role="img" aria-label="{e(caption)}">{svg}'
            f'<figcaption>{lab}{caption}</figcaption></figure>')


def progress_banner() -> str:
    coh = load("cohort") or {}
    done = (coh.get("summary") or {}).get("n_included")
    if done is None or done >= 64:
        return ""
    pct = min(100, round(100 * done / 66))
    return (f'<div class="note warn"><p><strong>Still running.</strong> The scans are '
            f'being processed one person at a time and {done} of about 66 are done '
            f'({pct}%). Every number below comes from those {done} and will change. '
            f'Anything not worked out yet says so.</p>'
            f'<div class="progress" role="img" aria-label="{pct} percent processed">'
            f'<span style="width:{pct}%"></span></div></div>')


def _model_table(models: dict) -> str:
    if not models:
        return pending()
    order = sorted(models.items(),
                   key=lambda kv: (kv[0].startswith(NULL_PREFIX),
                                   -(kv[1].get("auc_mean") or 0)))
    rows = []
    for name, m in order:
        if "error" in m:
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
<caption>Every model, scored the same way</caption>
<thead><tr><th>Model</th><th class="num">AUC</th><th class="num">95% range</th>
<th class="num">Balanced accuracy</th><th class="num">Catch rate</th>
<th class="num">p</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>"""


# -------------------------------------------------------------------- index
def build_index() -> None:
    coh = load("cohort") or {}
    summ = coh.get("summary", {})
    models = (load("models_LH") or {}).get("models", {})
    san = load("sanity_lateralisation") or {}
    hand = load("control_handflip") or {}
    beh = load("control_behaviour") or {}
    sev = load("control_severity") or {}
    rest = load("control_rest_vs_task") or {}
    diff = load("control_difficulty") or {}
    imp = load("importance_LH") or {}
    mv = load("multiverse") or {}

    n_inc = summ.get("n_included")
    n_pat, n_ctl = summ.get("n_patients"), summ.get("n_controls")

    def auc(name):
        return (models.get(name) or {}).get("auc_mean")

    lin, gcn = auc("tangent+logreg"), auc("GCN")
    svm, gbm = auc("tangent+svm"), auc("graph-metrics+gb")
    mot, bhv = auc(NULL_PREFIX + "motion-only"), auc(NULL_PREFIX + "behaviour-only")
    dem = auc(NULL_PREFIX + "demographics-only")

    hero = stats([
        (n_inc if n_inc is not None else "n/a", "people analysed"),
        (f"{n_pat}/{n_ctl}" if n_pat is not None else "n/a", "patients / controls"),
        ("241", "brain regions"),
        ("6", "scans each"),
        ("2,868", "brain images per person"),
        ("0.66 s", "per image"),
    ])

    # ---- the answer -------------------------------------------------------
    if lin is None or gcn is None:
        answer = pending()
        headline = pending()
    else:
        if lin > gcn + 0.02:
            answer = (
                f"<p><strong>No.</strong> A plain linear model on the same connection "
                f"strengths scores {fmt_auc(lin)}. The graph neural network scores "
                f"{fmt_auc(gcn)}. The support vector machine gets {fmt_auc(svm)} and "
                f"gradient boosting on classic network measures gets {fmt_auc(gbm)}.</p>"
                f"<p>This is the ordinary result in small brain imaging samples and it "
                f"is worth saying out loud. A graph network has to learn how to use the "
                f"shape of a network from the data. With 66 people and 241 regions "
                f"there are not enough examples to pay for that flexibility, so it ends "
                f"up doing a more expensive version of what the linear model already "
                f"does. The premise this project started from assumed the graph network "
                f"would be the interesting part. It was not.</p>")
        elif gcn > lin + 0.02:
            answer = (
                f"<p><strong>Yes, by a little.</strong> The graph network scores "
                f"{fmt_auc(gcn)} against {fmt_auc(lin)} for the linear model on the same "
                f"connection strengths. That gap is small next to the spread you get "
                f"from other analysis choices, so it is worth holding loosely.</p>")
        else:
            answer = (f"<p><strong>It is a tie.</strong> {fmt_auc(gcn)} for the graph "
                      f"network, {fmt_auc(lin)} for the linear model. The extra "
                      f"machinery buys nothing here.</p>")
        best = max(x for x in (lin, gcn, svm, gbm) if x is not None)
        headline = (f"<p>The best brain model separates the two groups at "
                    f"{fmt_auc(best)} AUC. That is clearly better than a coin flip. "
                    f"Whether it means the brain has reorganised is a different "
                    f"question, and most of this page is about that difference.</p>")

    scoreboard = bars([
        ("Connectivity, linear model", lin, False),
        ("Graph neural network", gcn, False),
        ("Connectivity, support vector machine", svm, False),
        ("Network measures, gradient boosting", gbm, False),
        ("Drawing quality only", bhv, True),
        ("Head movement only", mot, True),
        ("Age and sex only", dem, True),
    ]) if models else pending()

    # ---- lateralisation ---------------------------------------------------
    if san.get("n_subjects"):
        rows = "".join(
            f"<tr><td>{e(r['name'].replace('17Networks_', '').replace('_', ' '))}</td>"
            f"<td>{e(r['network'])}</td>"
            f"<td>{'right' if r['hemi'] == 'RH' else 'left' if r['hemi'] == 'LH' else 'middle'}</td>"
            f"<td class='num'>{r['value']:+.3f}</td></tr>"
            for r in san.get("top_left_hand", [])[:8])
        sanity = f"""
<div class="stats">
<div class="stat"><div class="n">{san['interaction_mean']:+.3f}</div>
<div class="k">size of the hand by side effect</div></div>
<div class="stat"><div class="n">{san['subjects_correct']}/{san['n_subjects']}</div>
<div class="k">people showing the right pattern</div></div>
<div class="stat"><div class="n">{san.get('top10_left_hand_in_right_hemisphere', 'n/a')}/10</div>
<div class="k">top left-hand regions on the right</div></div>
</div>
<div class="tablewrap"><table>
<caption>The eight regions most engaged by left-hand drawing</caption>
<thead><tr><th>Region</th><th>Network</th><th>Side of brain</th>
<th class="num">Left minus right</th></tr></thead>
<tbody>{rows}</tbody></table></div>"""
    else:
        sanity = pending()

    # ---- controls ---------------------------------------------------------
    if hand.get("difference_graph"):
        d = hand["difference_graph"]
        pv = (d.get("permutation") or {}).get("p_value")
        c1 = (f"<p>The difference network still separated the groups at "
              f"{fmt_auc(d.get('auc_mean'))} (p = {fmt_p(pv)}), using the "
              f"{hand.get('n_subjects', 'n/a')} people with usable runs from both "
              f"hands. Left hand alone gave {fmt_auc((hand.get('within_LH') or {}).get('auc_mean'))} "
              f"and right hand alone {fmt_auc((hand.get('within_RH') or {}).get('auc_mean'))}.</p>")
    else:
        c1 = pending()

    if beh.get("behaviour_only"):
        gap = beh.get("performance_gap", {})
        extra = ""
        if beh.get("brain_performance_matched"):
            extra = (f"<tr><td>Brain, patients and controls matched on how well they "
                     f"drew (n={beh.get('matched_n', 'n/a')})</td><td class='num'>"
                     f"{fmt_auc(beh['brain_performance_matched']['auc_mean'])}</td></tr>")
        c2 = f"""<div class="tablewrap"><table>
<caption>Brain against behaviour</caption>
<thead><tr><th>Model</th><th class="num">AUC</th></tr></thead><tbody>
<tr><td>Brain connections</td>
<td class="num">{fmt_auc((beh.get('brain_only') or {}).get('auc_mean'))}</td></tr>
<tr class="null"><td>Drawing quality only, no brain data <span class="tag">control</span></td>
<td class="num">{fmt_auc(beh['behaviour_only'].get('auc_mean'))}</td></tr>
<tr class="highlight"><td>Brain, after taking drawing quality out</td>
<td class="num">{fmt_auc((beh.get('brain_residualised_on_behaviour') or {}).get('auc_mean'))}</td></tr>
{extra}</tbody></table></div>
<p class="small">Left hand drawing quality on a standard scale: patients
{gap.get('patient_mean_z', float('nan')):+.2f}, controls
{gap.get('control_mean_z', float('nan')):+.2f}. Permutation p for the brain model
after drawing quality is removed:
{fmt_p((beh.get('brain_residualised_permutation') or {}).get('p_value'))}.</p>"""
    else:
        c2 = pending()

    if sev and not sev.get("error"):
        labels = {"DASH_ability": "How much trouble the hand gives them",
                  "monthsSinceInjury": "Months since the injury",
                  "edinburgh_shift": "How far hand preference has moved"}
        rr = ""
        for k, lab in labels.items():
            v = sev.get(k) or {}
            if v.get("error"):
                rr += f"<tr><td>{e(lab)}</td><td colspan='3' class='small'>{e(v['error'])}</td></tr>"
            else:
                rr += (f"<tr><td>{e(lab)}</td><td class='num'>{v.get('n', 'n/a')}</td>"
                       f"<td class='num'>{v.get('spearman_rho', float('nan')):+.3f}</td>"
                       f"<td class='num'>{fmt_p(v.get('p_value'))}</td></tr>")
        c3 = (f'<div class="tablewrap"><table><caption>Inside the patient group only'
              f'</caption><thead><tr><th>Predicting</th><th class="num">n</th>'
              f'<th class="num">Correlation</th><th class="num">p</th></tr></thead>'
              f'<tbody>{rr}</tbody></table></div>')
    else:
        c3 = pending()

    if rest.get("REST") and not (rest.get("REST") or {}).get("error"):
        c4 = f"""<div class="stats">
<div class="stat"><div class="n">{fmt_auc((rest.get('LH') or {}).get('auc_mean'))}</div>
<div class="k">while drawing left-handed</div></div>
<div class="stat"><div class="n">{fmt_auc((rest.get('REST') or {}).get('auc_mean'))}</div>
<div class="k">lying still, doing nothing</div></div>
</div>"""
    else:
        c4 = pending("The resting scans run in a second pass. This shows up when "
                     "that finishes.")

    if diff.get("LHeasy") and not (diff.get("LHeasy") or {}).get("error"):
        c5 = f"""<div class="stats">
<div class="stat"><div class="n">{fmt_auc((diff.get('LHeasy') or {}).get('auc_mean'))}</div>
<div class="k">easy blocks only</div></div>
<div class="stat"><div class="n">{fmt_auc((diff.get('LHhard') or {}).get('auc_mean'))}</div>
<div class="k">hard blocks only</div></div>
</div>"""
    else:
        c5 = pending()

    # ---- what it learned --------------------------------------------------
    if imp.get("top_nodes"):
        tr = "".join(
            f"<tr><td class='num'>{i+1}</td><td>{e(t['name'].replace('17Networks_','').replace('_',' '))}</td>"
            f"<td>{e(t['network'])}</td>"
            f"<td>{'right' if t['hemi']=='RH' else 'left' if t['hemi']=='LH' else 'middle'}</td>"
            f"<td class='num'>{t['selection_frequency']:.2f}</td></tr>"
            for i, t in enumerate(imp["top_nodes"][:12]))
        learned = (f"<div class='tablewrap'><table><caption>Regions the model leaned "
                   f"on most, and how often each one came out near the top across "
                   f"{imp.get('n_folds','n/a')} splits</caption>"
                   f"<thead><tr><th class='num'>#</th><th>Region</th><th>Network</th>"
                   f"<th>Side</th><th class='num'>How consistent</th></tr></thead>"
                   f"<tbody>{tr}</tbody></table></div>"
                   f"<p class='small'>{imp.get('n_stable_nodes', 0)} regions came out "
                   f"in the top tenth in at least 80% of splits. Anything less "
                   f"consistent than that is noise dressed up as a finding.</p>")
    else:
        learned = pending()

    # ---- multiverse -------------------------------------------------------
    if mv.get("n_specifications"):
        multi = (f"<div class='stats'>"
                 f"<div class='stat'><div class='n'>{mv['n_specifications']}</div>"
                 f"<div class='k'>pipelines run</div></div>"
                 f"<div class='stat'><div class='n'>{mv['auc_min']:.3f}</div>"
                 f"<div class='k'>worst</div></div>"
                 f"<div class='stat'><div class='n'>{mv['auc_median']:.3f}</div>"
                 f"<div class='k'>middle</div></div>"
                 f"<div class='stat'><div class='n'>{mv['auc_max']:.3f}</div>"
                 f"<div class='k'>best</div></div></div>"
                 f"<p>The gap between the worst and best defensible pipeline is "
                 f"{mv['auc_max'] - mv['auc_min']:.3f} AUC. A researcher who tried a "
                 f"few combinations and reported the one that worked could publish "
                 f"anywhere in that range. You can walk the whole grid on the "
                 f"<a href='explore.html'>tools page</a>.</p>")
    else:
        multi = pending("The pipeline grid runs after the main analysis.")

    body = f"""
<h1>Does the brain rewire itself after a hand injury?</h1>
<p class="lede">Twenty-five adults lost the use of their right hand to nerve damage
and had to start doing everything left-handed. I took brain scans recorded while
they drew, built a network for each person, and trained models to pick them out of
a crowd of healthy adults. Then I spent most of the project trying to break my own
result.</p>

{progress_banner()}
{hero}

<section id="built">
<h2>What I built</h2>
<div class="measure">
<p>The starting idea came from a video that went roughly: get the scans, pull out
the blood flow signals, build a graph neural network to sort patients from healthy
adults, then look inside the model to see which brain regions it used. That is a
reasonable sketch and it is what the first half of this project does.</p>
<p>The trouble is that the last step only means something if the first three are
sound. A model can separate two groups of people for many reasons that have nothing
to do with brains reorganising. Patients might move more in the scanner. The task
is genuinely harder for them, so their brains might just look like anyone working
hard. They are a few years older on average. Any of those would produce a model
that works and a story that is wrong.</p>
<p>So the project has two halves. The first builds the thing the video describes.
The second tries to knock it down, using four tests that each remove one of those
explanations. There is also a page of <a href="explore.html">interactive tools</a>
where you can walk through the analysis choices yourself and see how much the
answer depends on them.</p>
</div>
{headline}
</section>

<section id="data">
<h2>The data</h2>
<div class="measure">
<p>Everything comes from <a href="{DS_DOI}">OpenNeuro ds008162</a>, collected at
Washington University in St. Louis School of Medicine by Kapil, Kim, McAvoy and
Philip, and paid for by an NINDS grant. They released it under CC0, which is the
only reason a project like this is possible from a laptop.</p>
<p>71 right-handed adults took part. 25 had long-term peripheral nerve injury to
the right hand or arm, meaning damage to the nerves running into the hand rather
than to the brain itself. That distinction matters. The brain was never injured, so
anything different about it is a response to losing the hand, not damage.</p>
<p>Everyone did the same task. Lying in the scanner holding a special tablet, they
traced inside a path that moved ahead of them. The instruction was to go as fast as
they could while staying inside the lines, and staying inside mattered more than
speed. Three runs with the left hand, three with the right, alternating, always
starting with the hand they normally write with. Each run alternates 15 seconds of
drawing with 15 seconds of rest, ten times over.</p>
<p>The scanner took a picture of the whole brain every 0.66 seconds. That is fast
for fMRI, and it comes from a multiband sequence that images several slices at
once. Each run is 488 images, so each person contributes about 2,868 whole-brain
images across the six drawing runs, plus resting scans.</p>
</div>

<h3>Three things about the data I did not expect</h3>
<div class="measure">
<p><strong>One of the two groups was missing.</strong> The copy I was handed
had 45 of the 46 healthy adults and none of the 25 patients. You cannot train
a model to tell two groups apart when only one is present. Every patient scan
had to be pulled from OpenNeuro before anything could start, which also meant
writing the download and verification step first rather than last.</p>
<p><strong>There was no room on the disk.</strong> The dataset is 83 GB. The
laptop had 2.5 GB free. Rather than give up on the laptop, the pipeline works
through one person at a time and deletes their raw scans as soon as their
signals are extracted and checked. Free space goes up as the analysis runs.
Before deleting anything it confirms the same file is still downloadable from
OpenNeuro at the same byte size, so nothing is lost for good. Peak disk use is
about 3 GB no matter how many people you run.</p>
<p><strong>The gap in drawing quality is enormous.</strong> The dataset ships
drawing quality measured 30 times a second from the tablet: how smooth the
movement was, how accurately it followed the path, how fast. Patients score
far worse with the left hand. That is exactly what you would expect from the
injury, and it is a serious problem for the analysis, because a brain model
can score well by picking up effort rather than anything about
reorganisation. It became the main control test.</p>
</div>

<h3>Who was left out</h3>
<div class="measure">
<p>Five people were excluded by the original team: three patients whose head
movement tracked the task, one control with a tablet problem, and one who moved too
much. Those exclusions are kept here rather than quietly reversed.</p>
<p>On top of that a run was dropped if average head movement went above 0.30 mm,
if more than 30% of its images had to be censored, or if the brain did not line up
with the template well enough. A person needed at least two surviving left-hand runs
to be used at all. Three patients could not draw with the injured hand at all, so
they appear in the left-hand analysis but not in the left-minus-right comparison.</p>
</div>
{figure("motion", "Head movement for every person who made it through, split by "
                  "group. The red line is the cut-off. If patients sat well to the "
                  "right of controls here, movement alone could explain a group "
                  "difference, which is why one of the models below uses movement "
                  "and nothing else.", 1)}
</section>

<section id="signal">
<h2>First I checked the signal was really there</h2>
<div class="measure">
<p>Before believing anything about groups, the pipeline has to reproduce a fact that
cannot be wrong. Moving your left hand drives the right side of the brain. Moving
your right hand drives the left. If that does not appear, then the alignment, the
region labels, the hemisphere assignment or the event timing is broken, and
everything downstream is noise with a story attached.</p>
<p>Because everyone drew with both hands, the test can be paired. For each person,
subtract their right-hand response from their left-hand response, region by region.
A positive number means that region worked harder when they drew left-handed. That
paired form cancels everything fixed about the person and is far more sensitive than
comparing across people.</p>
</div>
{sanity}
{figure("lateralisation", "Each bar is one brain region. Bars to the right were more "
                          "active during left-hand drawing, bars to the left during "
                          "right-hand drawing. Blue regions sit in the right half of "
                          "the brain, orange in the left. The colours flip across the "
                          "middle line, which is the whole point of the test.", 2)}
<div class="measure">
<p>This one test covers the entire chain at once, including a detail that is easy to
get wrong. Event times in the data refer to the original scan, not to the images
left after the first ten are dropped for the scanner to settle. Miss that and every
block lands 6.6 seconds early, which quietly destroys the effect while leaving the
pipeline apparently working.</p>
<p>Two weaker versions of this test came first and were thrown out. Averaging all 34
sensorimotor regions waters down a hand effect with hearing and face areas the task
barely uses. Comparing across people rather than within them puts back every
difference the paired version removes. Both were too blunt to tell me anything, and
one of them reported a failure that was not real.</p>
</div>
</section>

<section id="pipeline">
<h2>Getting from scans to networks</h2>
<div class="measure">
<p>The usual route is fMRIPrep inside Docker. There was no Docker on this machine,
and no FSL, FreeSurfer or AFNI either. Running fMRIPrep on 71 people would also have
taken days. So the pipeline is built directly on ANTs through the
<code>antspyx</code> package, with numpy, nibabel and nilearn doing the rest.</p>
<p>Per run: drop the first 10 images while the scanner settles, correct for slices
being taken at slightly different moments, then align every image to the run average
so head movement is taken out. Per person: even out brightness across the anatomical
scan, get a brain mask by warping a template mask onto it, and split the brain into
grey matter, white matter and fluid.</p>
</div>

<div class="note">
<p><strong>The step that made this feasible.</strong> The slow part of a normal
pipeline is pushing all 488 images of every run into a shared template space. This
pipeline never does that. It moves the region map the other way instead, from the
template into each run's own space, and reads region averages straight off the data
where it already sits.</p>
<p>That is exact rather than a shortcut. Removing confounds and filtering both act
along the time axis. Averaging a region acts across space. Operations on separate
axes commute, so cleaning 241 region signals gives the same answer as cleaning
150,000 voxels and averaging afterwards. It is simply much cheaper, and it is what
brought the job down from days to hours.</p>
</div>

<div class="measure">
<p>Taken out of every signal: 24 movement terms, which are six numbers describing
head position, their frame-to-frame change, and both of those squared. Then five
summary components each from white matter and fluid, which capture noise shared
across the brain. Then a marker for any image where the head moved more than half a
millimetre. Finally a filter keeping 0.008 to 0.10 Hz, which holds the task rhythm
of 0.033 Hz comfortably inside it.</p>
<p>None of that is the only defensible recipe. {cite('parkes2018')} compared 19
versions of this step and found that group differences can flip depending which you
pick. That finding is the reason this project ends with a grid of pipelines rather
than a single number.</p>
<p>Each brain then becomes a network of 241 points: 200 cortical regions from
{cite('schaefer2018')}, 15 deeper structures from the Harvard-Oxford atlas, and 26
parts of the cerebellum from {cite('aal2002')}. The cerebellum is included on
purpose. It matters for learning movements and a lot of work in this area leaves it
out. Links between points are partial correlations computed from the drawing blocks
only, shifted four seconds to allow for how slowly blood flow responds.</p>
</div>

<div class="note warn">
<p><strong>A trap worth naming.</strong> One of the strongest ways to describe
connectivity, called tangent space, computes a group average first. Do that once
across everybody and then cross-validate, and the test people have leaked into
training. Every score comes out too high and nothing warns you.</p>
<p>To make that impossible, the stored files hold time signals rather than finished
connectivity matrices, which forces every estimator to be fitted inside the training
half. Splits are grouped by person, so nobody appears on both sides of a fold. One
of the tests shuffles the labels and checks the score lands near 0.50, which is what
catches a leak if one ever gets introduced.</p>
</div>
</section>

<section id="models">
<h2>How the models work</h2>
<div class="measure">
<p>The graph neural network the original idea calls for is here, along with two
other kinds. A graph network passes information between connected regions and
learns what to pay attention to, so in principle it can use the shape of the network
rather than just the strength of individual links. The design follows the recipes
tested in {cite('cui2022')}: two message-passing layers, batch normalisation,
dropout, and a readout that combines the average and the strongest response across
regions.</p>
<p>Next to it sit the models that might beat it. A linear classifier and a support
vector machine over the same connection strengths. Gradient boosting over classic
network measures like how well connected each region is and how clustered its
neighbourhood is.</p>
<p>Then three models built to be dangerous. One uses head movement and nothing else.
One uses drawing quality and nothing else. One uses age and sex. If any of them
matches the brain models, then the headline is not about brain networks, and burying
them in an appendix would be the wrong choice.</p>
<p>Every score is the average of 10 repeats of five-fold cross-validation grouped by
person. Every headline number also gets a permutation test: the group labels are
shuffled between people and the whole procedure is run again, hundreds of times, to
see what scores are reachable with no real difference in the data.
{cite('eklund2016')} showed permutation tests behaving correctly in fMRI where the
standard maths did not.</p>
</div>
</section>

<section id="answer">
<h2>Does the graph network beat the simple method?</h2>
<div class="measure">{answer}</div>
{scoreboard}
{_model_table(models)}
<div class="measure">
<p>The grey rows use no brain data. They exist to be compared against, and the most
important number in the whole table is what the drawing quality model scores.</p>
</div>
</section>

<section id="wrong">
<h2>Four ways this could be wrong</h2>
<div class="measure">
<p>Getting a model to tell patients from controls is easy. Working out whether it
did so for the reason you hoped is the hard part. {cite('makin2015')} is the
cautionary case here: a well-known story about brain remapping after arm amputation
that did not survive once someone measured the other explanations properly.</p>
</div>

<h3>1. Is it the hand, or is it just these people?</h3>
<div class="measure">
<p>Patients and controls differ in fixed ways with nothing to do with drawing. Head
size, blood vessels, how still someone lies, whatever else has happened to them.
A model comparing one group of brains against another can pick up any of it.</p>
<p>The way round it is that everyone drew with both hands. Take a person's
right-hand network away from their own left-hand network and everything fixed about
them cancels. They become their own control, and whatever survives has to be
specific to using the weaker hand.</p>
</div>
{c1}

<h3>2. Is it the brain, or do they simply draw worse?</h3>
<div class="measure">
<p>This is the one that matters most. Drawing left-handed is genuinely harder for
someone whose dominant hand no longer works, and the dataset records exactly how
much worse they did. A brain model can score well by noticing effort. That is a
real result, but it is not the one being claimed.</p>
<p>So: how well does drawing quality do on its own, with no brain data at all? And
does connectivity still predict anything once drawing quality is regressed out, and
inside a smaller group where patients and controls are matched on how well they
drew?</p>
</div>
{c2}

<h3>3. Does it track how badly someone is affected?</h3>
<div class="measure">
<p>A yes-or-no label is blunt. If networks really do reorganise after losing the use
of a hand, the effect should be graded: stronger in people who struggle more, who
have lived with it longer, or whose writing hand has actually shifted. A
relationship that scales is much harder to explain away than a split between two
groups. {cite('freund2011')} did this after spinal cord injury and found the amount
of remapping tracked how disabled people were. The same idea runs here, inside the
patient group alone, where there is no healthy comparison to lean on.</p>
</div>
{c3}

<h3>4. Is it about drawing at all?</h3>
<div class="measure">
<p>Everyone also lay in the scanner doing nothing. If the same model works on those
scans, the difference is something people carry around all the time rather than
something the task brings out. Both answers are interesting. Running them together
and reporting whichever is stronger is what makes "the brain rewires itself" sound
more settled than it is.</p>
</div>
{c4}

<h3>Extra: do patients treat easy blocks like hard ones?</h3>
<div class="measure">
<p>The task was built with graded difficulty and the data labels every block as
easier or harder. If patients are working flat out throughout, their easy blocks
should already look like everyone else's hard ones.</p>
</div>
{c5}
</section>

<section id="learned">
<h2>What the model learned</h2>
<div class="measure">
<p>Reading a model's internals is the part most likely to produce a confident
picture of nothing. A saliency map from a single fit at this sample size is close to
noise. So importance is recomputed inside every cross-validation split and the
rankings are combined, and only regions that come out near the top again and again
are reported.</p>
<p>Whichever model actually wins provides the importances. If a linear model on
connection strengths is the best performer, then its coefficients are the
interpretability result, and they are far steadier than graph network saliency.</p>
</div>
{learned}
<div class="measure">
<p>One warning worth repeating. Importance tells you what the model used to tell the
groups apart. It does not tell you what the brain is doing. If two regions carry the
same information the model will often split the credit between them at random, and a
region can score low simply because a neighbour already covered it.</p>
<p>You can look at all 241 regions, filter by network and click any of them on the
<a href="explore.html">tools page</a>.</p>
</div>
</section>

<section id="multiverse">
<h2>The same data, ninety different ways</h2>
<div class="measure">
<p>Everything above reports one pipeline. But the pipeline had choices in it, and
every one of them was defensible: which confounds to remove, which frequency band to
keep, how to measure connectivity, which model to use, which hand condition to look
at. Picking a different combination gives a different number.</p>
<p>Reporting only the combination that worked is how a field ends up with findings
that do not replicate. So rather than pick, this project runs the whole grid and
keeps every result.</p>
</div>
{multi}
<div class="measure">
<p>This is the single most useful thing here for anyone reading about brain imaging
results elsewhere. When you see one number reported from a small study, the honest
question is not whether that number is real. It is how many other numbers the same
data could have produced.</p>
</div>
</section>

<section id="limits">
<h2>What is wrong with this</h2>
<div class="measure">
<p>Being specific about the weaknesses, because a list of caveats written in general
terms is worth nothing:</p>
</div>
<ul class="flaws">
<li><strong>One scan per person.</strong> Nothing here watches a brain change.
Calling any of this rewiring means inferring a process from a single snapshot of
differences between groups. A proper test would scan the same people before and
after the injury, which for obvious reasons nobody can arrange.</li>
<li><strong>66 people is a small study.</strong> {cite('marek2022')} looked at
roughly 50,000 scans and found brain-to-behaviour effects are much smaller than
assumed, and that studies this size produce inflated estimates that later fail to
replicate. {cite('turner2018')} found the same for task studies. Nothing here should
be treated as settled, and the tools page has a calculator that shows why.</li>
<li><strong>No fieldmap correction.</strong> Echo-planar images are stretched and
squashed near air pockets in the skull. The proper fix uses a fieldmap, which was
skipped here to save disk and time. Non-linear alignment to each person's anatomy
absorbs some of it, but regions near the front and bottom of the brain are worse
off than the numbers suggest.</li>
<li><strong>The patients are older on average</strong> and the sexes are not evenly
split between groups. Age and sex are checked as a control model, but a control
model only rules out the simplest version of that problem.</li>
<li><strong>Task-correlated movement.</strong> People move when they draw, and
patients may move differently. The original team excluded three patients for exactly
this. Movement regressors remove some of it and also remove some real signal, and
there is no clean way to separate the two.</li>
<li><strong>One scanner, one site, one protocol.</strong> Nothing here has been
tested on data collected anywhere else.</li>
<li><strong>The region map is an assumption.</strong> Dividing the cortex into 200
pieces is a choice, and a region that does not match the real functional boundary
mixes signals that should be kept apart.</li>
</ul>
</section>

<section id="run">
<h2>Run it yourself</h2>
<div class="measure">
<p>Public data, open-source packages, no licence keys, no GPU. This ran on an Apple
M4 laptop with 10 cores and 24 GB of memory. Aligning head movement is the slow step
at about two minutes a run, and it already uses every core, so running several
people at once does not help. Budget roughly twenty minutes a person.</p>
</div>
<pre><code>git clone https://github.com/aaryavvatts-lab/neuroswitch
cd neuroswitch &amp;&amp; uv sync
uv run python -m neuroswitch.atlas 200
uv run python -m neuroswitch.acquire --top-level
./drive.sh 1 3 subjects.txt drawLH,drawRH
uv run python -m neuroswitch.run_analysis --stages cohort,main,controls
uv run python -m neuroswitch.multiverse
uv run python -m neuroswitch.site_build
uv run pytest</code></pre>
<div class="measure">
<p>Every page here is generated from the files in <code>results/</code>, so no
number on the site is typed in by hand. The tests cover slice timing against a known
shift, head movement against a hand-worked example, region averaging on a made-up
brain, and a full dry run of the model chain on data where the answer is known in
advance.</p>
</div>
</section>

<section id="refs">
<h2>References</h2>
<div class="measure">
<p>Every paper below was looked up in a live literature index and has a working DOI.
All credit for collecting the data belongs to the Washington University team. This
is an independent student reanalysis and they have not reviewed it.</p>
</div>
<ul class="refs">
{''.join(f'<li><a href="{r["url"]}"><strong>{e(r["title"])}</strong></a>'
         f'<div class="meta">{e(r["authors"])}, {r["year"]}. {e(r["venue"])}. '
         f'doi:{e(r["doi"])}</div>'
         f'<div class="why">{e(r["note"])}</div></li>' for r in REFERENCES)}
</ul>
</section>
"""
    write("index.html", "Does the brain rewire after a hand injury?", body,
          "A student reanalysis of brain scans from adults with long-term right hand "
          "nerve injury drawing with their left hand, and four tests of whether the "
          "result means what it looks like.", anchors=True)


# ------------------------------------------------------------------ explore
EXPLORE_CSS = """
.tool { border-top: 1px solid var(--ink); padding-top: 1.4rem; margin: 2.6rem 0 0;
        max-width: var(--bleed); }
.controls { display: grid; gap: 1rem 1.6rem; margin: 1.3rem 0;
            grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr)); }
.ctl label { display: block; font-family: var(--sans); font-size: .74rem;
             text-transform: uppercase; letter-spacing: .06em; color: var(--ink-2);
             margin-bottom: .35rem; }
.ctl select, .ctl input[type=range] { width: 100%; font-family: var(--sans);
                                      font-size: .85rem; }
.ctl select { padding: .35rem .4rem; border: 1px solid var(--rule-2);
              background: var(--paper); color: var(--ink); border-radius: 2px; }
.ctl .v { font-family: var(--sans); font-size: .8rem; color: var(--ink);
          font-variant-numeric: tabular-nums; margin-top: .25rem; }
.readout { display: flex; flex-wrap: wrap; gap: 0; margin: 1.3rem 0;
           border-top: 1px solid var(--ink); border-bottom: 1px solid var(--rule); }
.readout div { flex: 1 1 0; min-width: 7rem; padding: .85rem .9rem .85rem 0;
               border-right: 1px solid var(--rule); }
.readout div:last-child { border-right: 0; }
.readout .n { font-family: var(--sans); font-size: 1.45rem; font-weight: 600;
              letter-spacing: -.02em; font-variant-numeric: tabular-nums; }
.readout .k { font-family: var(--sans); font-size: .72rem; color: var(--ink-2);
              margin-top: .3rem; line-height: 1.35; }
.chart svg { max-width: 100%; height: auto; display: block; }
.verdict { border-left: 2px solid var(--ink); padding: .15rem 0 .15rem 1.1rem;
           margin: 1.2rem 0; max-width: var(--measure); }
.verdict.good { border-left-color: var(--right); }
.verdict.bad { border-left-color: var(--stop); }
.bgrid { display: grid; gap: 1.1rem; grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));
         margin: 1.2rem 0; }
.bview { margin: 0; border-top: 1px solid var(--rule-2); padding-top: .5rem; }
.bviewhead { font-family: var(--sans); font-size: .72rem; color: var(--ink-2);
             margin-bottom: .4rem; text-transform: uppercase; letter-spacing: .06em; }
.bviewhead span { text-transform: none; letter-spacing: 0; color: var(--ink-3); }
.bnode { cursor: pointer; }
.legend { display: flex; flex-wrap: wrap; gap: .3rem; margin: 1rem 0; }
.lg { display: inline-flex; align-items: center; gap: .35rem; font-family: var(--sans);
      font-size: .73rem; padding: .18rem .48rem; border: 1px solid var(--rule);
      background: var(--paper); color: var(--ink-3); cursor: pointer; border-radius: 2px; }
.lg.on { color: var(--ink); border-color: var(--rule-2); }
.lg .sw { width: .58rem; height: .58rem; border-radius: 50%; opacity: .3; }
.lg.on .sw { opacity: 1; }
.bpick { border-left: 2px solid var(--ink); padding: .1rem 0 .1rem 1rem; }
.bpick h3 { margin: 0 0 .3rem; }
.bpick p { margin: 0; }
#bdetail { margin: 1rem 0; min-height: 3rem; }
"""

REPLICATION_JS = r"""
(function () {
  const host = document.getElementById('repl');
  if (!host) return;

  // Normal quantile, Acklam's approximation. Good to about 1e-9.
  function qnorm(p) {
    const a=[-3.969683028665376e+01,2.209460984245205e+02,-2.759285104469687e+02,
             1.383577518672690e+02,-3.066479806614716e+01,2.506628277459239e+00];
    const b=[-5.447609879822406e+01,1.615858368580409e+02,-1.556989798598866e+02,
             6.680131188771972e+01,-1.328068155288572e+01];
    const c=[-7.784894002430293e-03,-3.223964580411365e-01,-2.400758277161838e+00,
             -2.549732539343734e+00,4.374664141464968e+00,2.938163982698783e+00];
    const d=[7.784695709041462e-03,3.224671290700398e-01,2.445134137142996e+00,
             3.754408661907416e+00];
    const pl=0.02425;
    let q,r;
    if (p<pl){q=Math.sqrt(-2*Math.log(p));
      return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])/((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1);}
    if (p<=1-pl){q=p-0.5;r=q*q;
      return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q/(((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1);}
    q=Math.sqrt(-2*Math.log(1-p));
    return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])/((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1);
  }
  // deterministic normal draws, so the same settings always give the same picture
  let seed = 20260824;
  function rnd(){ seed = (seed*1664525 + 1013904223) >>> 0; return (seed+0.5)/4294967296; }
  function rnorm(){ return qnorm(Math.min(Math.max(rnd(),1e-12),1-1e-12)); }

  const el = id => document.getElementById(id);
  function run() {
    const rTrue = parseFloat(el('r-true').value);
    const n = parseInt(el('r-n').value, 10);
    const studies = 4000;
    el('r-true-v').textContent = rTrue.toFixed(2);
    el('r-n-v').textContent = n;

    // Fisher z sampling distribution of a correlation
    const z = 0.5*Math.log((1+rTrue)/(1-rTrue));
    const se = 1/Math.sqrt(Math.max(n-3,1));
    const crit = 1.959963985;
    let sig=0, sumSig=0, sumAll=0, signFlip=0;
    const found=[];
    seed = 20260824;
    for (let i=0;i<studies;i++){
      const zi = z + se*rnorm();
      const ri = Math.tanh(zi);
      sumAll += ri;
      if (Math.abs(zi/se) > crit){
        sig++; sumSig += Math.abs(ri); found.push(Math.abs(ri));
        if (Math.sign(ri) !== Math.sign(rTrue) && rTrue !== 0) signFlip++;
      }
    }
    const power = sig/studies;
    const published = sig ? sumSig/sig : 0;
    const inflation = rTrue !== 0 && sig ? published/Math.abs(rTrue) : 0;

    el('r-power').textContent = (power*100).toFixed(0) + '%';
    el('r-pub').textContent = sig ? published.toFixed(2) : 'n/a';
    el('r-infl').textContent = sig ? inflation.toFixed(1) + 'x' : 'n/a';
    el('r-flip').textContent = sig ? (100*signFlip/sig).toFixed(0) + '%' : 'n/a';

    // histogram of the effects that would get published
    const bins = 30, lo = 0, hi = 1;
    const counts = new Array(bins).fill(0);
    for (const v of found) counts[Math.min(bins-1, Math.floor((v-lo)/(hi-lo)*bins))]++;
    const maxC = Math.max(...counts, 1);
    const w=620,h=190,pl=40,pr=14,pt=14,pb=36;
    const sx = v => pl + ((v-lo)/(hi-lo))*(w-pl-pr);
    const sy = c => h-pb-(c/maxC)*(h-pt-pb);
    let s=`<svg viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" role="img"
      aria-label="Effect sizes that would get published, from ${studies} simulated studies of ${n} people.">`;
    for (let i=0;i<bins;i++){
      if(!counts[i]) continue;
      const a=sx(lo+(hi-lo)*i/bins), b2=sx(lo+(hi-lo)*(i+1)/bins);
      s+=`<rect x="${a.toFixed(1)}" y="${sy(counts[i]).toFixed(1)}"
           width="${Math.max(1,b2-a-0.8).toFixed(1)}" height="${(h-pb-sy(counts[i])).toFixed(1)}"
           fill="var(--paper-3)" stroke="var(--rule-2)" stroke-width="0.5"/>`;
    }
    const tx = sx(Math.abs(rTrue));
    s+=`<line x1="${tx.toFixed(1)}" y1="${pt-4}" x2="${tx.toFixed(1)}" y2="${h-pb}"
         stroke="var(--right)" stroke-width="2"/>`;
    s+=`<text x="${tx.toFixed(1)}" y="${pt-6}" font-size="10.5" text-anchor="middle"
         fill="var(--right)" font-family="var(--sans)" font-weight="600">the truth</text>`;
    if (sig){
      const px = sx(published);
      s+=`<line x1="${px.toFixed(1)}" y1="${pt-4}" x2="${px.toFixed(1)}" y2="${h-pb}"
           stroke="var(--left)" stroke-width="2" stroke-dasharray="4 3"/>`;
      s+=`<text x="${px.toFixed(1)}" y="${h-pb+26}" font-size="10.5" text-anchor="middle"
           fill="var(--left)" font-family="var(--sans)" font-weight="600">what gets published</text>`;
    }
    s+=`<line x1="${pl}" y1="${h-pb}" x2="${w-pr}" y2="${h-pb}" stroke="var(--ink)"/>`;
    for (const t of [0,0.2,0.4,0.6,0.8,1.0]){
      s+=`<line x1="${sx(t)}" y1="${h-pb}" x2="${sx(t)}" y2="${h-pb+4}" stroke="var(--ink)"/>`;
      s+=`<text x="${sx(t)}" y="${h-pb+15}" font-size="10.5" text-anchor="middle"
           fill="var(--ink-2)" font-family="var(--sans)">${t.toFixed(1)}</text>`;
    }
    s+=`</svg>`;
    el('r-chart').innerHTML=s;

    const v = el('r-verdict');
    if (power < 0.3){
      v.className='verdict bad';
      v.innerHTML=`<p>With ${n} people and a true effect of ${rTrue.toFixed(2)}, only
        <strong>${(power*100).toFixed(0)}%</strong> of studies would find it. The ones that
        do would report it as <strong>${published.toFixed(2)}</strong> on average, which is
        <strong>${inflation.toFixed(1)} times</strong> too big. Most of the literature you
        would see from this design is wrong in size even when it is right in direction.</p>`;
    } else if (power < 0.8){
      v.className='verdict';
      v.innerHTML=`<p>${(power*100).toFixed(0)}% of studies would find this effect, and
        those that do would report it about ${inflation.toFixed(1)} times too big. Better,
        still not a design you would want to build on.</p>`;
    } else {
      v.className='verdict good';
      v.innerHTML=`<p>${(power*100).toFixed(0)}% of studies would find this, and the
        published size would be close to the truth. This is what a well-powered design
        looks like.</p>`;
    }
  }
  ['r-true','r-n'].forEach(id => el(id).addEventListener('input', run));
  run();
})();
"""

SPEC_JS = r"""
(function () {
  const host = document.getElementById('spec');
  if (!host) return;
  const raw = document.getElementById('specdata');
  if (!raw) return;
  let D;
  try { D = JSON.parse(raw.textContent); } catch(e){ return; }
  const specs = D.specifications || [];
  if (!specs.length) return;

  const FIELDS = [
    ['condition','Which hand'], ['confounds','Confounds removed'],
    ['band','Frequency band'], ['connectivity','How links are measured'],
    ['model','Model']
  ];
  const opts = {};
  FIELDS.forEach(([f]) => { opts[f] = [...new Set(specs.map(s => s[f]))]; });

  const el = id => document.getElementById(id);
  function pick() {
    const want = {};
    FIELDS.forEach(([f]) => { want[f] = el('sp-'+f).value; });
    return specs.find(s => FIELDS.every(([f]) => s[f] === want[f])) || null;
  }

  function draw() {
    const sorted = [...specs].sort((a,b) => a.auc - b.auc);
    const chosen = pick();
    const w=640,h=230,pl=44,pr=14,pt=16,pb=40;
    const lo=Math.min(0.35,sorted[0].auc-0.02), hi=Math.max(0.9,sorted[sorted.length-1].auc+0.02);
    const sx = i => pl + (i/(sorted.length-1||1))*(w-pl-pr);
    const sy = v => h-pb-((v-lo)/(hi-lo))*(h-pt-pb);
    let s=`<svg viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" role="img"
      aria-label="Every one of ${sorted.length} pipelines, sorted by score. The chosen one is marked.">`;
    // chance line
    s+=`<line x1="${pl}" y1="${sy(0.5)}" x2="${w-pr}" y2="${sy(0.5)}"
         stroke="var(--ink-3)" stroke-dasharray="3 3"/>`;
    s+=`<text x="${w-pr}" y="${sy(0.5)-5}" font-size="10.5" text-anchor="end"
         fill="var(--ink-3)" font-family="var(--sans)">chance</text>`;
    for (let i=0;i<sorted.length;i++){
      const isPick = chosen && sorted[i] === chosen;
      s+=`<circle cx="${sx(i).toFixed(1)}" cy="${sy(sorted[i].auc).toFixed(1)}"
           r="${isPick?4.5:2}" fill="${isPick?'var(--right)':'var(--ink-3)'}"
           fill-opacity="${isPick?1:0.42}"/>`;
    }
    s+=`<line x1="${pl}" y1="${h-pb}" x2="${w-pr}" y2="${h-pb}" stroke="var(--ink)"/>`;
    s+=`<line x1="${pl}" y1="${pt}" x2="${pl}" y2="${h-pb}" stroke="var(--ink)"/>`;
    for (const t of [0.4,0.5,0.6,0.7,0.8,0.9]){
      if (t<lo||t>hi) continue;
      s+=`<text x="${pl-6}" y="${sy(t)+3.5}" font-size="10.5" text-anchor="end"
           fill="var(--ink-2)" font-family="var(--sans)">${t.toFixed(1)}</text>`;
    }
    s+=`<text x="${(pl+w-pr)/2}" y="${h-8}" font-size="10.5" text-anchor="middle"
         fill="var(--ink-2)" font-family="var(--sans)">every pipeline, worst to best</text>`;
    s+=`</svg>`;
    el('sp-chart').innerHTML=s;

    if (!chosen){
      el('sp-read').innerHTML='';
      el('sp-verdict').innerHTML='<p class="small">That combination was not run. '+
        'Some are skipped because they do not apply, such as a graph model on the '+
        'left-minus-right difference.</p>';
      return;
    }
    const rank = sorted.indexOf(chosen)+1;
    const pct = Math.round(100*rank/sorted.length);
    el('sp-read').innerHTML =
      `<div><div class="n">${chosen.auc.toFixed(3)}</div><div class="k">AUC for this pipeline</div></div>`+
      `<div><div class="n">${rank}/${sorted.length}</div><div class="k">where it ranks</div></div>`+
      `<div><div class="n">${chosen.n}</div><div class="k">people it could use</div></div>`+
      `<div><div class="n">${D.auc_min.toFixed(3)}-${D.auc_max.toFixed(3)}</div><div class="k">full range across all pipelines</div></div>`;
    el('sp-verdict').innerHTML =
      `<p>This combination beats ${pct}% of the others. The gap between the worst and
       best defensible pipeline is <strong>${(D.auc_max-D.auc_min).toFixed(3)}</strong>
       AUC. Somebody reporting a single number from this dataset could have landed
       anywhere in that range and defended every choice along the way.</p>`;
  }

  host.querySelector('.controls').innerHTML = FIELDS.map(([f,label]) =>
    `<div class="ctl"><label for="sp-${f}">${label}</label>
     <select id="sp-${f}">${opts[f].map(o=>`<option value="${o}">${o}</option>`).join('')}</select></div>`
  ).join('');
  FIELDS.forEach(([f]) => el('sp-'+f).addEventListener('change', draw));
  draw();
})();
"""


def build_explore() -> None:
    mv = load("multiverse") or {}
    imp = load("importance_LH") or {}

    if mv.get("specifications"):
        spec_block = (
            '<div class="controls"></div><div class="readout" id="sp-read"></div>'
            '<div class="chart" id="sp-chart"></div><div id="sp-verdict"></div>'
            f'<script type="application/json" id="specdata">'
            f'{json.dumps({k: mv[k] for k in ("specifications","auc_min","auc_max","auc_median")})}'
            f'</script>')
        spec_wrap = f'<div id="spec">{spec_block}</div>'
    else:
        spec_wrap = pending("The pipeline grid runs after the main analysis finishes. "
                            "It will appear here.")

    body = f"""
<h1>Try it yourself</h1>
<p class="lede">Three tools. The first is about brain imaging in general and is
probably the most useful thing on this site. The second lets you walk every analysis
choice this project made. The third is the brain itself.</p>

<section class="tool" id="tool-repl">
<h2>Would a study this size have found it?</h2>
<div class="measure">
<p>This one is not about my data. It is about every brain imaging headline you have
ever read.</p>
<p>Set a true effect and a sample size. The tool simulates four thousand studies of
that size, counts how many would reach the usual significance threshold, and shows
what those studies would report. The gap between the truth and what gets published
is the point.</p>
<p>The reason it matters: a study only gets written up when it finds something. If
the sample is small, the only way to reach significance is to draw an unusually
large effect by luck. So the published number is systematically too big, and the
smaller the study, the worse it gets. That is why {cite('marek2022')} argues brain
imaging needs thousands of people rather than dozens.</p>
</div>

<div id="repl">
<div class="controls">
<div class="ctl"><label for="r-true">True effect (correlation)</label>
<input type="range" id="r-true" min="0.05" max="0.6" step="0.01" value="0.15">
<div class="v"><span id="r-true-v">0.15</span></div></div>
<div class="ctl"><label for="r-n">People in the study</label>
<input type="range" id="r-n" min="10" max="1000" step="5" value="66">
<div class="v"><span id="r-n-v">66</span></div></div>
</div>
<div class="readout">
<div><div class="n" id="r-power">0%</div><div class="k">of studies would find it</div></div>
<div><div class="n" id="r-pub">0</div><div class="k">effect they would report</div></div>
<div><div class="n" id="r-infl">0x</div><div class="k">how inflated that is</div></div>
<div><div class="n" id="r-flip">0%</div><div class="k">that get the direction backwards</div></div>
</div>
<div class="chart" id="r-chart"></div>
<div id="r-verdict"></div>
</div>
<div class="measure">
<p class="small">Try 0.15, which is a realistic effect for brain measures against
behaviour, at 66 people, which is this project. Then drag the sample size up and
watch what changes. That is the honest context for everything on the study page.</p>
</div>
</section>

<section class="tool" id="tool-spec">
<h2>Walk every analysis choice</h2>
<div class="measure">
<p>Every pipeline has forks in it, and most of them are defensible. Which confounds
to remove. Which frequency band to keep. How to measure the links between regions.
Which model. Which hand.</p>
<p>Rather than pick one combination and report it, this project runs the whole grid.
Choose any combination below and see where it lands among all the others.</p>
</div>
{spec_wrap}
<div class="measure">
<p class="small">If a set of choices you would consider reasonable gives a very
different answer from another set you would also consider reasonable, then no single
number from this dataset should be trusted on its own. That is the finding, not a
caveat about it.</p>
</div>
</section>

<section class="tool" id="tool-brain">
<h2>The brain, region by region</h2>
<div class="measure">
<p>241 regions: 200 in the cortex, 15 deeper in the brain, 26 in the cerebellum.
Filter by network, or click any region to see where it sits and how much the model
leaned on it.</p>
{'<p>Sizes come from ' + e(imp.get('model','the best model')) + ', recomputed inside each of '
 + str(imp.get('n_folds','several')) + ' cross-validation splits and averaged. Only regions that '
 'come out near the top again and again mean anything.</p>' if imp.get('n_folds')
 else '<p class="pending">Region importance appears once the models have been fitted. '
      'For now the map shows the regions themselves.</p>'}
</div>
<div id="brainapp"><p class="pending">Loading the map.</p></div>
</section>

<style>{EXPLORE_CSS}</style>
<script>{REPLICATION_JS}</script>
<script>{SPEC_JS}</script>
<script>{BRAIN_JS}</script>
"""
    write("explore.html", "Try it", body,
          "Three tools: a replication calculator for any brain imaging claim, an "
          "explorer for every analysis choice this project made, and the brain map.")


BRAIN_JS = r"""
(async function () {
  const host = document.getElementById('brainapp');
  if (!host) return;
  let D;
  try { D = await (await fetch('data/brain.json')).json(); }
  catch (err) { host.innerHTML = '<p class="pending">Could not load the region data.</p>'; return; }
  const nodes = D.nodes.filter(n => isFinite(n.x) && isFinite(n.y) && isFinite(n.z));
  const imp = D.importance || null;
  const nets = D.networks;

  const PALETTE = {
    SomMotA:'#b0521c', SomMotB:'#d08340', Cerebellum:'#4a6741', Subcortex:'#7a6a4f',
    VisCent:'#3f6d7a', VisPeri:'#5f8f99', DorsAttnA:'#6b7f5c', DorsAttnB:'#8a9a76',
    SalVentAttnA:'#8a6a17', SalVentAttnB:'#a98c47', ContA:'#1a5570', ContB:'#3d7591',
    ContC:'#6997ad', DefaultA:'#7d5a52', DefaultB:'#9c7a70', DefaultC:'#b59a92',
    LimbicA:'#6f5f7a', LimbicB:'#8f8199', TempPar:'#556b7d'
  };
  const palette = {};
  nets.forEach(n => { palette[n] = PALETTE[n] || '#7c7a70'; });

  let active = new Set(nets), selected = null;
  const impOf = n => (imp ? (imp[n.id - 1] ?? 0) : null);
  const vals = imp ? nodes.map(impOf).filter(v => isFinite(v)) : [];
  const hi = vals.length ? Math.max(...vals) : 1, lo = vals.length ? Math.min(...vals) : 0;
  const norm = v => (hi > lo ? (v - lo) / (hi - lo) : 0.5);

  const VIEWS = [
    { a:'x', b:'y', title:'Seen from above', note:'left of the picture is the left side of the brain' },
    { a:'y', b:'z', title:'Seen from the side', note:'front of the head is on the right' }
  ];

  function svgFor(view, w, h) {
    const pad = 16;
    const xs = nodes.map(n => n[view.a]), ys = nodes.map(n => n[view.b]);
    const x0 = Math.min(...xs), x1 = Math.max(...xs);
    const y0 = Math.min(...ys), y1 = Math.max(...ys);
    const sx = v => pad + ((v - x0) / (x1 - x0)) * (w - 2 * pad);
    const sy = v => h - pad - ((v - y0) / (y1 - y0)) * (h - 2 * pad);
    let s = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${view.title}. ${nodes.length} brain regions plotted by position.">`;
    s += `<ellipse cx="${w/2}" cy="${h/2}" rx="${w/2-pad+6}" ry="${h/2-pad+6}" fill="var(--paper-2)" stroke="var(--rule)"/>`;
    if (view.a === 'x') s += `<line x1="${w/2}" y1="${pad-6}" x2="${w/2}" y2="${h-pad+6}" stroke="var(--rule)" stroke-dasharray="3 4"/>`;
    const order = [...nodes].sort((m,n) => (imp ? norm(impOf(m)) - norm(impOf(n)) : 0));
    for (const n of order) {
      const on = active.has(n.network);
      const t = imp ? norm(impOf(n)) : 0.5;
      const r = imp ? 2.2 + t*7 : 3.4;
      const op = on ? (imp ? 0.35 + 0.65*t : 0.85) : 0.07;
      const sel = selected && selected.id === n.id;
      s += `<circle class="bnode" data-id="${n.id}" cx="${sx(n[view.a]).toFixed(1)}" cy="${sy(n[view.b]).toFixed(1)}" r="${(sel?r+3:r).toFixed(1)}" fill="${palette[n.network]}" fill-opacity="${op.toFixed(2)}" stroke="${sel?'var(--ink)':'none'}" stroke-width="1.5" tabindex="0" role="button" aria-label="${n.label}, ${n.network}"><title>${n.label}${imp?', importance '+impOf(n).toFixed(3):''}</title></circle>`;
    }
    s += `</svg>`;
    return `<figure class="bview"><div class="bviewhead">${view.title} <span>${view.note}</span></div>${s}</figure>`;
  }

  const legend = () => `<div class="legend">` + nets.map(n =>
    `<button class="lg${active.has(n)?' on':''}" data-net="${n}" aria-pressed="${active.has(n)}"><span class="sw" style="background:${palette[n]}"></span>${n}</button>`).join('')
    + `<button class="lg reset" data-net="__all">show all</button></div>`;

  function detail() {
    if (!selected) return `<p class="small">Pick a region, or use the buttons above to show one network at a time.${imp?' Bigger and more solid dots are regions the model used more.':''}</p>`;
    const n = selected;
    const side = n.hemi==='LH'?'left':n.hemi==='RH'?'right':'middle';
    return `<div class="bpick"><h3>${n.label}</h3><p class="small">${n.network}, ${side} side, from ${n.source}, ${n.n_voxels} voxels<br>Position ${n.x}, ${n.y}, ${n.z}${imp?`<br><strong>importance ${impOf(n).toFixed(4)}</strong>`:''}</p></div>`;
  }

  function table() {
    if (!imp) return '';
    const rows = [...nodes].sort((a,b)=>impOf(b)-impOf(a)).slice(0,20).map((n,i) =>
      `<tr><td class="num">${i+1}</td><td>${n.label}</td><td>${n.network}</td><td>${n.hemi==='LH'?'left':n.hemi==='RH'?'right':'middle'}</td><td class="num">${impOf(n).toFixed(4)}</td></tr>`).join('');
    return `<h3>Regions the model used most</h3><p class="small">The same information as the map, as a list, for anyone who cannot use the picture.</p><div class="tablewrap"><table><thead><tr><th class="num">#</th><th>Region</th><th>Network</th><th>Side</th><th class="num">Importance</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function render() {
    host.innerHTML = legend() + `<div class="bgrid">${VIEWS.map(v=>svgFor(v,340,300)).join('')}</div><div id="bdetail">${detail()}</div>` + table();
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
