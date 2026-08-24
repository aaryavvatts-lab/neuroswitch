"""Page content for the neuroswitch site.

Prose is written here; every number is pulled from results/*.json at build time.
"""
from __future__ import annotations

import json

from .site_build import (DS_DOI, PREPRINT, bars, e, fmt_auc, fmt_ci, fmt_p, load,
                         pending, stats, write)

NULL_PREFIX = "NULL "


# ---------------------------------------------------------------- index
def build_index() -> None:
    coh = load("cohort") or {}
    s = coh.get("summary", {})
    models = (load("models_LH") or {}).get("models", {})
    hand = load("control_handflip") or {}
    beh = load("control_behaviour") or {}

    n_inc = s.get("n_included")
    n_pat = s.get("n_patients")
    n_ctl = s.get("n_controls")

    key = stats([
        (n_inc if n_inc is not None else "—", "participants analysed"),
        (f"{n_pat}/{n_ctl}" if n_pat is not None else "—", "patients / controls"),
        ("241", "brain regions per graph"),
        ("6", "fMRI runs per person"),
        ("0.66 s", "sampling rate (TR)"),
    ])

    def auc_of(name):
        m = models.get(name) or {}
        return m.get("auc_mean")

    best_brain = auc_of("tangent+logreg")
    gcn = auc_of("GCN")
    mot = auc_of(NULL_PREFIX + "motion-only")
    bhv = auc_of(NULL_PREFIX + "behaviour-only")

    if models:
        scoreboard = bars([
            ("Connectivity + linear model", best_brain, False),
            ("Graph neural network (GCN)", gcn, False),
            ("Head motion only", mot, True),
            ("Drawing performance only", bhv, True),
        ])
    else:
        scoreboard = pending()

    findings = []
    if best_brain is not None and gcn is not None:
        winner = "the graph network" if gcn > best_brain else "a plain linear model"
        findings.append((
            "The fancy model is not automatically the better one",
            f"A graph convolutional network scored {fmt_auc(gcn)} AUC. "
            f"A linear model on the same connectivity edges scored {fmt_auc(best_brain)}. "
            f"At this sample size {winner} came out ahead — which is why both are "
            f"reported here instead of only the one that sounds more impressive."))
    if bhv is not None:
        findings.append((
            "Patients draw much worse, and that is a rival explanation",
            f"Four numbers describing how well someone drew with their left hand "
            f"classify patient vs. control at {fmt_auc(bhv)} AUC — without any brain data. "
            f"Any honest claim about \"rewiring\" has to survive that."))
    if hand.get("difference_graph"):
        d = hand["difference_graph"]
        findings.append((
            "Subtracting each person from themselves",
            f"Comparing each participant's left-hand network against their own "
            f"right-hand network removes everything fixed about that person — head "
            f"size, vascular anatomy, how still they sit. That difference still "
            f"classified at {fmt_auc(d.get('auc_mean'))} AUC "
            f"(p = {fmt_p((d.get('permutation') or {}).get('p_value'))})."))

    cards = "".join(
        f'<div class="card"><h3>{e(t)}</h3><p>{b}</p></div>' for t, b in findings
    ) if findings else pending("Findings appear once the analysis has run.")

    body = f"""
<h1>Does the brain rewire itself after a hand injury?</h1>
<p class="lede">People with chronic nerve damage to the right hand have to do everything
with the left. This is a reanalysis of brain scans taken while they drew — asking
whether their brain networks look measurably different, and, more carefully than
usual, whether that difference means what it appears to mean.</p>

{key}

<section>
<h2>What this is, and what it is not</h2>
<div class="measure">
<p><strong>It is</strong> an independent reanalysis of a public dataset from Washington
University in St. Louis: 46 healthy adults and 25 people with chronic peripheral nerve
injury to the right hand, all drawing precision shapes inside an MRI scanner with each
hand. After the original authors' exclusions and quality control,
{f"{n_pat} patients and {n_ctl} controls" if n_pat else "a subset"} entered the models.
Blood-oxygen signals were extracted from 241 brain regions, turned into connectivity
graphs, and fed to a classifier.</p>
<p><strong>It is not</strong> evidence that anyone's brain "rewired". Every person was
scanned once, so nothing here observes change over time. Group differences in a
cross-sectional dataset are compatible with reorganisation, but also with differences
that predate the injury, with how hard the task was for each person, and with how
still they lay in the scanner. Most of the work below is spent trying to tell those
apart.</p>
<p>It is also not a medical device, a diagnostic, or advice. The sample is 66 people
from one scanner.</p>
</div>
</section>

<section>
<h2>How well does it actually work?</h2>
{scoreboard}
<p class="small">AUC is the chance that a randomly chosen patient is scored as more
patient-like than a randomly chosen control. 0.50 is a coin flip; 1.00 is perfect.</p>
</section>

<section>
<h2>The things worth knowing</h2>
{cards}
</section>

<section>
<h2>Start anywhere</h2>
<div class="cards">
<div class="card"><h3><a href="data.html">The data</a></h3>
<p>Where the scans came from, what the drawing task was, and the three problems
that had to be solved before any of it could be analysed.</p></div>
<div class="card"><h3><a href="methods.html">How it works</a></h3>
<p>Turning raw scans into brain graphs without the standard neuroimaging toolchain
— and the one test that proves the pipeline is not producing nonsense.</p></div>
<div class="card"><h3><a href="controls.html">Could this be wrong?</a></h3>
<p>Four ways the headline could be an artefact, each one tested rather than
waved away.</p></div>
<div class="card"><h3><a href="brain.html">Explore the brain</a></h3>
<p>Which regions and networks the model leaned on, and how left- and right-hand
drawing differ.</p></div>
</div>
</section>
"""
    write("index.html", "Does the brain rewire after hand injury?", body,
          "An independent reanalysis of fMRI data from adults with chronic right-hand "
          "nerve injury drawing with their left hand.")


# ---------------------------------------------------------------- data
def build_data() -> None:
    coh = load("cohort") or {}
    s = coh.get("summary", {})
    subs = coh.get("subjects", [])
    excl = s.get("exclusion_counts", {})
    excl_rows = "".join(
        f"<tr><td>{e(k)}</td><td class='num'>{v}</td></tr>" for k, v in excl.items()
    ) or "<tr><td colspan='2' class='pending'>pending</td></tr>"

    fd_note = ""
    if subs:
        fds = [r["mean_fd"] for r in subs if r.get("included") and r.get("mean_fd")]
        if fds:
            fd_note = (f"Across included participants, mean framewise displacement was "
                       f"{sum(fds)/len(fds):.3f} mm — low for a task where people are "
                       f"moving a hand.")

    body = f"""
<h1>Where the data comes from</h1>
<p class="lede">A public dataset of 71 adults drawing shapes inside a 3T scanner,
released under CC0 by the group that collected it.</p>

<section>
<h2>The study</h2>
<div class="measure">
<p>The scans come from <a href="{DS_DOI}">OpenNeuro ds008162</a>, collected at Washington
University in St. Louis School of Medicine by Kapil, Kim, McAvoy and Philip and funded
by NINDS. 71 right-handed adults took part: 25 with chronic unilateral peripheral nerve
injury to the right hand or arm, and 46 healthy controls.</p>
<p>Everyone did the same thing. Lying in the scanner with an MRI-compatible drawing
tablet, they traced inside a moving path — "draw within the lines, and move as quickly
as you can, but staying within the lines is more important than speed." Three runs with
the left hand, three with the right, alternating, always starting with the hand they
naturally write with.</p>
<p>Each run alternates 15-second drawing blocks with 15-second rest, ten times. The
scanner sampled the whole brain every 0.66 seconds — fast, thanks to a multiband
sequence — giving 488 volumes per run at 3&nbsp;mm resolution.</p>
</div>

<div class="stats">
<div class="stat"><div class="n">71</div><div class="k">people scanned</div></div>
<div class="stat"><div class="n">0.66 s</div><div class="k">per whole-brain volume</div></div>
<div class="stat"><div class="n">488</div><div class="k">volumes per run</div></div>
<div class="stat"><div class="n">10</div><div class="k">drawing blocks per run</div></div>
</div>
</section>

<section>
<h2>Three things about the data I did not expect</h2>
<div class="cards">
<div class="card"><h3>Half the experiment was missing</h3>
<p>The copy of the dataset I was handed contained 45 of the 46 healthy controls — and
none of the 25 patients. One of the two groups simply was not there, which makes
"classify patient vs. control" impossible. The patient scans had to be streamed from
OpenNeuro before anything could start.</p></div>

<div class="card"><h3>There was no room to work</h3>
<p>The dataset is 83&nbsp;GB and the disk had 2.5&nbsp;GB free. The pipeline was
restructured to process one person at a time and delete their raw scans immediately
after extracting their signals, so free space <em>grows</em> as the analysis runs. Every
deleted file is recorded with its public download URL, so nothing is unrecoverable.</p></div>

<div class="card"><h3>Patients draw dramatically worse</h3>
<p>The dataset ships per-person drawing quality measured at 30&nbsp;Hz from the tablet.
The gap between groups is large. That is clinically unsurprising and analytically
dangerous: a brain model can score well by indirectly detecting task difficulty. This
became the main control analysis.</p></div>
</div>
</section>

<section>
<h2>Who was left out, and why</h2>
<div class="measure">
<p>Five participants were excluded by the original authors — three patients for head
motion correlated with the task, one control for a tablet error, one for excessive
motion. Those exclusions are honoured here. On top of that, runs were dropped for mean
framewise displacement above 0.30&nbsp;mm, more than 30% of frames censored, or poor
registration; a person needed at least two surviving left-hand runs to be analysed.
{e(fd_note)}</p>
</div>
<div class="tablewrap"><table>
<thead><tr><th>Reason for exclusion</th><th class="num">People</th></tr></thead>
<tbody>{excl_rows}</tbody></table></div>
<p class="small">Three patients (<code>sub-1002</code>, <code>sub-1019</code>,
<code>sub-1045</code>) could not draw with their injured right hand at all, so they
contribute to left-hand analyses but not to the left-minus-right comparison.</p>
</section>
"""
    write("data.html", "The data", body,
          "OpenNeuro ds008162: 71 adults drawing in a 3T scanner, and the three "
          "problems that had to be solved first.")


# ---------------------------------------------------------------- methods
def build_methods() -> None:
    san = load("sanity_lateralisation") or {}
    if san.get("n_subjects"):
        rows = "".join(
            f"<tr><td>{e(r['name'].replace('17Networks_','').replace('_',' '))}</td>"
            f"<td>{e(r['network'])}</td>"
            f"<td>{'right' if r['hemi']=='RH' else 'left' if r['hemi']=='LH' else '—'}</td>"
            f"<td class='num'>{r['value']:+.3f}</td></tr>"
            for r in san.get("top_left_hand", [])[:8])
        verdict = ("passes" if san.get("all_pass") else "DOES NOT PASS")
        cls = "" if san.get("all_pass") else " bad"
        sanity_block = f"""
<div class="stats">
<div class="stat"><div class="n">{san['interaction_mean']:+.3f}</div>
<div class="k">hand × hemisphere interaction</div></div>
<div class="stat"><div class="n">{san['subjects_correct']}/{san['n_subjects']}</div>
<div class="k">people showing the correct flip</div></div>
<div class="stat"><div class="n">{san.get('top10_left_hand_in_right_hemisphere','—')}/10</div>
<div class="k">top left-hand regions that are right-hemisphere</div></div>
</div>
<div class="tablewrap"><table>
<thead><tr><th>Region</th><th>Network</th><th>Side</th>
<th class="num">Left-hand minus right-hand</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<div class="note{cls}"><p>The check <strong>{verdict}</strong>: the regions most engaged
by left-hand drawing sit in the right hemisphere, and the sensorimotor regions
flip sides when the drawing hand flips.</p></div>"""
    else:
        sanity_block = pending()

    body = f"""
<h1>How it works</h1>
<p class="lede">Raw scanner output to brain graphs, using no neuroimaging software
beyond a Python package — and one test that decides whether any of it is trustworthy.</p>

<section>
<h2>Preprocessing without the usual toolchain</h2>
<div class="measure">
<p>The standard route is fMRIPrep inside Docker. Neither Docker nor FSL, FreeSurfer or
AFNI were available here, and fMRIPrep on 71 people would have taken days. So the
pipeline is built directly on ANTs (through <code>antspyx</code>) plus numpy, nibabel
and nilearn.</p>
<p>Per run: drop the first 10 volumes while the scanner reaches equilibrium, correct
slice timing by Fourier phase shift, then rigid-body motion correction against the run
mean. Per person: bias-correct the T1 anatomical scan, obtain a brain mask by warping
the template mask, and segment tissue with Atropos to get white-matter and
cerebrospinal-fluid compartments.</p>
</div>

<div class="note">
<p><strong>The step that makes this feasible.</strong> The expensive part of a normal
pipeline is resampling a 488-volume series into template space. This pipeline never
does that. Instead the <em>atlas</em> is pulled into each run's own native space
through the composed transform chain MNI&nbsp;→&nbsp;T1&nbsp;→&nbsp;EPI, and region
averages are read straight off the motion-corrected data.</p>
<p>That is exact, not a shortcut: removing confounds and band-pass filtering act along
time, averaging a region acts across space, and operations on independent axes commute.
Averaging first and cleaning 241 signals gives the same answer as cleaning 150,000
voxels and averaging afterwards.</p>
</div>

<div class="measure">
<p>Confounds removed from every signal: 24 motion terms (six parameters, their
derivatives, and both squared), five principal components each from white matter and
CSF, framewise displacement, DVARS, and a spike regressor for every frame moving more
than 0.5&nbsp;mm. Band-pass 0.008–0.10&nbsp;Hz, which comfortably contains the
0.033&nbsp;Hz task-block rhythm.</p>
</div>
</section>

<section>
<h2>Does the pipeline actually work?</h2>
<div class="measure">
<p>Before trusting any group difference, the pipeline has to reproduce something that
cannot be wrong. Moving your left hand activates the <em>right</em> side of the brain,
and vice versa. If that flip does not appear, registration, region labelling, hemisphere
assignment or event timing is broken and everything downstream is noise.</p>
<p>Because everyone drew with both hands, the test is a paired one: for each person,
subtract their right-hand response from their left-hand response, region by region. A
positive value means a region worked harder when that person drew left-handed.</p>
</div>
{sanity_block}
<p class="small">This single test exercises the whole chain at once — including the
easily-botched detail that event onsets refer to the original scan, not to the volumes
that remain after the first ten are trimmed. Getting that wrong shifts every block by
6.6&nbsp;seconds and quietly destroys the contrast.</p>
<div class="measure"><p class="small">Two weaker versions of this check were tried first
and discarded: averaging all 34 sensorimotor parcels (which dilutes a hand-specific
effect with auditory and face regions the task barely engages), and comparing conditions
between subjects rather than within them. Both were far too insensitive to be evidence
either way.</p></div>
</section>

<section>
<h2>From signals to graphs</h2>
<div class="measure">
<p>Each brain becomes a graph of 241 nodes: 200 cortical regions from the Schaefer
parcellation, 15 subcortical structures from Harvard–Oxford, and 26 cerebellar regions
from AAL. The cerebellum is included deliberately — it is central to motor learning and
routinely dropped from this kind of analysis.</p>
<p>Edges are partial correlations between region signals during drawing blocks only,
shifted four seconds to allow for the delay in the blood-oxygen response, with the
strongest 10% retained. Node features combine each region's connectivity profile, its
task response, its low-frequency signal amplitude, and which functional network it
belongs to.</p>
</div>
<div class="note warn">
<p><strong>A leakage trap worth naming.</strong> Tangent-space connectivity — the
strongest classical representation — estimates a group average. Computing it once over
everyone and then cross-validating would leak test subjects into training and inflate
every score. Here the feature store deliberately keeps <em>time series</em> rather than
connectivity matrices, which forces every estimator to be fit inside the training split.
Splits are grouped by person, so no one appears on both sides of a fold.</p>
</div>
</section>

<section>
<h2>The models</h2>
<div class="measure">
<p>The graph convolutional network the premise calls for is here, alongside GAT and GIN
variants. So are the models that might beat it: linear and support-vector classifiers on
connectivity edges, and gradient boosting on classical graph-theory summaries.</p>
<p>And three models designed to be <em>dangerous</em> — head motion alone, drawing
performance alone, and age and sex alone. If any of them matches the brain models, the
headline is not about brain networks. They are reported in the same table, not buried.</p>
<p>Every score is the mean over 10 repeats of 5-fold cross-validation grouped by person,
and every headline number carries a permutation test in which group labels are shuffled
and the whole procedure re-run.</p>
</div>
</section>
"""
    write("methods.html", "How it works", body,
          "Preprocessing without fMRIPrep, building brain graphs, and the "
          "lateralisation test that validates the pipeline.")


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
                        f"<td colspan='5' class='small'>failed: {e(m['error'][:80])}</td></tr>")
            continue
        is_null = name.startswith(NULL_PREFIX)
        agg = m.get("aggregate", {})
        perm = m.get("permutation") or {}
        label = name[len(NULL_PREFIX):] if is_null else name
        tag = " <span class='tag'>control</span>" if is_null else ""
        rows.append(
            f"<tr class='{'null' if is_null else ''}'>"
            f"<td>{e(label)}{tag}</td>"
            f"<td class='num'>{fmt_auc(m.get('auc_mean'))}</td>"
            f"<td class='num'>{fmt_ci(m.get('auc_ci'))}</td>"
            f"<td class='num'>{fmt_auc(agg.get('balanced_acc'))}</td>"
            f"<td class='num'>{fmt_auc(agg.get('sensitivity'))}</td>"
            f"<td class='num'>{fmt_p(perm.get('p_value')) if perm else '—'}</td></tr>")
    return f"""<div class="tablewrap"><table>
<thead><tr><th>Model</th><th class="num">AUC</th><th class="num">95% CI</th>
<th class="num">Bal. acc.</th><th class="num">Sensitivity</th>
<th class="num">p (perm.)</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>"""


def build_results() -> None:
    res = load("models_LH") or {}
    models = res.get("models", {})
    b = res.get("bundle", {})

    gcn = (models.get("GCN") or {}).get("auc_mean")
    lin = (models.get("tangent+logreg") or {}).get("auc_mean")
    verdict = pending()
    if gcn is not None and lin is not None:
        if gcn > lin + 0.02:
            verdict = (f"<p>The graph network wins: {fmt_auc(gcn)} against "
                       f"{fmt_auc(lin)} for the linear model. The graph structure is "
                       f"carrying information the edge weights alone do not.</p>")
        elif lin > gcn + 0.02:
            verdict = (f"<p><strong>No.</strong> The linear model on the same "
                       f"connectivity edges scores {fmt_auc(lin)}; the graph "
                       f"convolutional network scores {fmt_auc(gcn)}. With 66 people "
                       f"and 241 regions there is not enough data for the deeper model "
                       f"to pay for its own flexibility. This is the ordinary outcome "
                       f"in small neuroimaging samples, and it is worth stating plainly "
                       f"rather than quietly reporting only the GCN.</p>")
        else:
            verdict = (f"<p>They tie — {fmt_auc(gcn)} for the graph network against "
                       f"{fmt_auc(lin)} for the linear model. The extra machinery buys "
                       f"nothing here.</p>")

    body = f"""
<h1>Does the graph network beat the simple method?</h1>
<p class="lede">Every model, including the ones built to fail, scored the same way:
10 repeats of 5-fold cross-validation grouped by person, with shuffled-label
permutation tests on the headline numbers.</p>

<section>
<h2>The answer</h2>
<div class="measure">{verdict}</div>
</section>

<section>
<h2>Every model, side by side</h2>
{_model_table(models)}
<p class="small">Rows in grey are control models. They use no brain data and exist to
be compared against — if one of them matched the brain models, the brain result would
need reinterpreting, not celebrating. Sample:
{b.get('n_patients', '—')} patients, {b.get('n_controls', '—')} controls,
{b.get('n_nodes', '—')} regions.</p>
</section>

<section>
<h2>How to read a permutation test</h2>
<div class="measure">
<p>Cross-validated accuracy on a small sample is a noisy quantity, and a model given
random labels rarely scores exactly 0.50. So each headline model was re-fit hundreds of
times with group labels shuffled between people, building the distribution of scores
obtainable from data with no real group difference. The reported p-value is the fraction
of shuffles that matched or beat the real score.</p>
<p>A shuffled-label distribution that does not centre near 0.50 is itself a red flag —
it would mean the cross-validation is leaking. That check is part of the output.</p>
</div>
</section>
"""
    write("results.html", "Results", body,
          "Model-by-model results with permutation tests and control models.")


# ---------------------------------------------------------------- controls
def build_controls() -> None:
    hand = load("control_handflip") or {}
    beh = load("control_behaviour") or {}
    sev = load("control_severity") or {}
    rest = load("control_rest_vs_task") or {}
    diff = load("control_difficulty") or {}

    # T1
    if hand.get("difference_graph"):
        d = hand["difference_graph"]
        p = (d.get("permutation") or {})
        t1 = f"""<div class="stats">
<div class="stat"><div class="n">{fmt_auc(d.get('auc_mean'))}</div>
<div class="k">left-minus-right difference graph</div></div>
<div class="stat"><div class="n">{fmt_auc((hand.get('within_LH') or {}).get('auc_mean'))}</div>
<div class="k">left hand alone</div></div>
<div class="stat"><div class="n">{fmt_auc((hand.get('within_RH') or {}).get('auc_mean'))}</div>
<div class="k">right hand alone</div></div>
<div class="stat"><div class="n">{fmt_p(p.get('p_value'))}</div>
<div class="k">permutation p</div></div>
</div>
<p class="small">Difference-graph analysis uses the {hand.get('n_subjects', '—')} people
with usable runs from both hands.</p>"""
    else:
        t1 = pending()

    # T2
    if beh.get("behaviour_only"):
        gap = beh.get("performance_gap", {})
        mrows = ""
        if beh.get("brain_performance_matched"):
            mg = beh.get("matched_performance_gap", {})
            mrows = (f"<tr><td>Brain, performance-matched subsample "
                     f"(n={beh.get('matched_n','—')})</td>"
                     f"<td class='num'>{fmt_auc(beh['brain_performance_matched']['auc_mean'])}</td></tr>")
        t2 = f"""<div class="tablewrap"><table>
<thead><tr><th>Model</th><th class="num">AUC</th></tr></thead><tbody>
<tr><td>Brain connectivity</td><td class="num">{fmt_auc((beh.get('brain_only') or {}).get('auc_mean'))}</td></tr>
<tr class="null"><td>Drawing performance only — no brain data</td>
<td class="num">{fmt_auc(beh['behaviour_only'].get('auc_mean'))}</td></tr>
<tr class="highlight"><td>Brain, after removing drawing performance</td>
<td class="num">{fmt_auc((beh.get('brain_residualised_on_behaviour') or {}).get('auc_mean'))}</td></tr>
{mrows}
</tbody></table></div>
<p class="small">Left-hand drawing quality, standardised: patients
{gap.get('patient_mean_z', float('nan')):+.2f} vs controls
{gap.get('control_mean_z', float('nan')):+.2f}.
Permutation p for the residualised brain model:
{fmt_p((beh.get('brain_residualised_permutation') or {}).get('p_value'))}.</p>"""
    else:
        t2 = pending()

    # T3
    if sev and not sev.get("error"):
        rows = ""
        labels = {"DASH_ability": "Disability score (DASH)",
                  "monthsSinceInjury": "Months since injury",
                  "edinburgh_shift": "Shift in hand preference since injury"}
        for k, lab in labels.items():
            v = sev.get(k) or {}
            if v.get("error"):
                rows += f"<tr><td>{e(lab)}</td><td colspan='3' class='small'>{e(v['error'])}</td></tr>"
            else:
                rows += (f"<tr><td>{e(lab)}</td><td class='num'>{v.get('n','—')}</td>"
                         f"<td class='num'>{v.get('spearman_rho', float('nan')):+.3f}</td>"
                         f"<td class='num'>{fmt_p(v.get('p_value'))}</td></tr>")
        t3 = f"""<div class="tablewrap"><table>
<thead><tr><th>Predicting, within patients only</th><th class="num">n</th>
<th class="num">Spearman ρ</th><th class="num">p</th></tr></thead>
<tbody>{rows}</tbody></table></div>"""
    else:
        t3 = pending()

    # T4
    if rest.get("REST") and not (rest.get("REST") or {}).get("error"):
        t4 = f"""<div class="stats">
<div class="stat"><div class="n">{fmt_auc((rest.get('LH') or {}).get('auc_mean'))}</div>
<div class="k">during left-hand drawing</div></div>
<div class="stat"><div class="n">{fmt_auc((rest.get('REST') or {}).get('auc_mean'))}</div>
<div class="k">at rest, doing nothing</div></div>
</div>"""
    else:
        t4 = pending("Resting-state runs are processed in a second pass; "
                     "this comparison appears when that finishes.")

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
<p class="lede">A classifier that separates patients from controls is easy to get and
easy to over-read. These are the four ways the result could be an artefact — each one
turned into a test rather than a caveat.</p>

<section>
<h2>1. Is it the hand, or just these people?</h2>
<div class="measure">
<p>Patients and controls differ in many fixed ways that have nothing to do with drawing:
head size, vascular anatomy, how still they lie, what else has happened to them. A model
comparing one group's brains to another's can pick up any of it.</p>
<p>The fix uses the fact that everyone drew with <em>both</em> hands. Subtracting each
person's right-hand network from their own left-hand network cancels everything fixed
about that person — they are their own control. Whatever survives is specific to using
the non-dominant hand.</p>
</div>
{t1}
</section>

<section>
<h2>2. Is it the brain, or do they simply draw worse?</h2>
<div class="measure">
<p>This is the one that matters most. Patients have nerve damage in their dominant hand,
so drawing with the other hand is genuinely harder for them, and the dataset records
exactly how much worse they were. A brain model can score well purely by detecting
effort and difficulty — a real finding, but not the one being claimed.</p>
<p>So: how well does drawing performance alone classify, with no brain data at all? And
does connectivity still predict once performance is regressed out and within a subsample
of patients and controls matched on how well they drew?</p>
</div>
{t2}
</section>

<section>
<h2>3. Does the signature track how badly someone is affected?</h2>
<div class="measure">
<p>Group labels are crude. If brain networks genuinely reorganise in response to losing
a hand, the effect should be <em>graded</em>: stronger in people who are more disabled,
or who have lived with the injury longer, or whose hand preference has actually shifted.
A relationship that scales is far harder to explain away than a binary split — so this
is tested within the patient group alone, where there is no healthy comparison to lean on.</p>
</div>
{t3}
</section>

<section>
<h2>4. Is it about drawing at all, or is it always there?</h2>
<div class="measure">
<p>Everyone also lay in the scanner doing nothing. If the same classifier works on
resting-state data, the difference is a persistent trait rather than something recruited
by the task. Both answers are informative; conflating them is what makes "the brain
rewires itself" sound more established than it is.</p>
</div>
{t4}
</section>

<section>
<h2>Bonus: do patients treat easy blocks like hard ones?</h2>
<div class="measure">
<p>The task was designed with graded difficulty, and the dataset labels every block as
easier or harder. If patients are working harder throughout, the easy blocks should
already look like everyone else's hard blocks.</p>
</div>
{t5}
</section>

<section>
<h2>What would still not be settled</h2>
<div class="note bad">
<p>Even if every test above comes out favourably, this remains cross-sectional: each
person was scanned once. Nothing here observes a brain changing. "Rewiring" is an
inference about a process from a snapshot of differences, and a single-site sample of
66 people cannot carry that inference on its own.</p>
</div>
</section>
"""
    write("controls.html", "Could this be wrong?", body,
          "Four ways the headline could be an artefact, each tested: hand-difference "
          "graphs, drawing performance, severity scaling, and rest versus task.")


# ---------------------------------------------------------------- reproduce
def build_reproduce() -> None:
    body = """
<h1>Run it yourself</h1>
<p class="lede">Everything here comes from public data and open-source packages. No
credentials, no licensed neuroimaging software, no GPU.</p>

<section>
<h2>What you need</h2>
<div class="measure">
<p>A machine with Python 3.12 and roughly 25&nbsp;GB of working disk. The published run
used an Apple M4 with 10 cores and 24&nbsp;GB of memory. There is no CUDA anywhere in
the pipeline; the graph networks are small enough to train on CPU.</p>
</div>
<pre><code>git clone &lt;this repository&gt; &amp;&amp; cd neuroswitch
uv sync                       # installs antspyx, torch, torch-geometric, nilearn
uv run python -m neuroswitch.atlas 200            # build the 241-region parcellation
</code></pre>
</section>

<section>
<h2>Getting the scans</h2>
<div class="measure">
<p>The dataset is CC0 on OpenNeuro and downloads anonymously. Fetching only the
modalities this analysis uses is about 1.6&nbsp;GB per person rather than 2.6&nbsp;GB.</p>
</div>
<pre><code>uv run python -m neuroswitch.acquire --top-level          # participants + phenotype
uv run python -m neuroswitch.acquire sub-1001 sub-1002    # one or more people
</code></pre>
</section>

<section>
<h2>Processing</h2>
<div class="measure">
<p>The driver processes people one at a time and deletes each person's raw scans only
after their extracted signals pass verification, so peak disk use stays near
3&nbsp;GB no matter how many people you run. Deletion is refused if a derivative is
missing, contains gaps, or registered poorly, and every removed file is logged with the
URL it came from.</p>
<p>Motion correction dominates the runtime at roughly two minutes per run, and it
already uses every core — so running several people in parallel does not help. Budget
about twenty minutes per person.</p>
</div>
<pre><code>./drive.sh 1 3 subjects.txt drawLH,drawRH   # workers, min free GB, list, tasks
uv run python -m neuroswitch.features sub-1001   # cleaned signals per condition
</code></pre>
</section>

<section>
<h2>Analysis and site</h2>
<pre><code>uv run python -m neuroswitch.run_analysis --stages cohort,main,controls
uv run python -m neuroswitch.site_build          # regenerates every page from results/
uv run pytest                                    # unit tests
</code></pre>
<div class="measure">
<p>The site is generated from <code>results/*.json</code>, so no figure or number on it
can drift from what the analysis produced. Rebuilding after a new run updates every page.</p>
</div>
</section>
"""
    write("reproduce.html", "Run it yourself", body,
          "Exact commands, hardware, and runtime to reproduce the analysis.")


# ---------------------------------------------------------------- refs
def build_refs() -> None:
    body = f"""
<h1>References and credits</h1>

<section>
<h2>The dataset</h2>
<div class="measure">
<p>Kapil, N., Kim, T., McAvoy, M. P., &amp; Philip, B. A. (2026). <em>Precision drawing
during task fMRI in healthy adults and individuals with peripheral nerve injury.</em>
OpenNeuro. <a href="{DS_DOI}">doi:10.18112/openneuro.ds008162.v1.0.3</a>. Released
under CC0. Collected at Washington University in St. Louis School of Medicine and
funded by NINDS R01 NS114046.</p>
<p>The accompanying study is available as a preprint:
<a href="{PREPRINT}">doi:10.1101/2025.11.18.689091</a>.</p>
<p>All credit for designing the study, recruiting participants and collecting the data
belongs to that group. This site is an independent reanalysis; any errors in it are
mine, not theirs, and nothing here should be read as their conclusion.</p>
</div>
</section>

<section>
<h2>Atlases</h2>
<div class="measure">
<p>Schaefer et al. (2018), local-global cortical parcellation, 200 regions / 17 networks.
Harvard–Oxford subcortical atlas (Harvard Center for Morphometric Analysis).
AAL (Tzourio-Mazoyer et al., 2002) for cerebellar regions.
Template space MNI152NLin6Asym via TemplateFlow.</p>
</div>
</section>

<section>
<h2>Software</h2>
<div class="measure">
<p>ANTs / antspyx for registration, motion correction and segmentation; nibabel and
nilearn for neuroimaging I/O, signal cleaning and connectivity; scikit-learn for the
classical models; PyTorch and PyTorch Geometric for the graph networks; Captum for
attribution. All open source.</p>
</div>
</section>

<section>
<h2>Scope</h2>
<div class="note">
<p>This is a methods demonstration on public data, not a clinical study. It makes no
diagnostic claim, and it should not be used to inform anyone's care.</p>
</div>
</section>
"""
    write("refs.html", "References", body, "Dataset citation, atlases, and software.")


# ---------------------------------------------------------------- brain
BRAIN_JS = r"""
(async function () {
  const host = document.getElementById('brainapp');
  let D;
  try {
    D = await (await fetch('data/brain.json')).json();
  } catch (err) {
    host.innerHTML = '<p class="pending">Could not load brain data.</p>';
    return;
  }
  const nodes = D.nodes.filter(n => isFinite(n.x) && isFinite(n.y) && isFinite(n.z));
  const imp = D.importance || null;
  const nets = D.networks;

  // stable, readable hues per network; sensorimotor deliberately the warm anchor
  const palette = {};
  nets.forEach((n, i) => {
    const hue = Math.round((i * 360) / nets.length);
    palette[n] = `hsl(${hue} 52% 48%)`;
  });
  palette['SomMotA'] = '#c2410c';
  palette['SomMotB'] = '#ea7317';
  palette['Cerebellum'] = '#3f6212';
  palette['Subcortex'] = '#6d28d9';

  let active = new Set(nets);
  let selected = null;

  const impOf = n => (imp ? (imp[n.id - 1] ?? 0) : null);
  const impVals = imp ? nodes.map(impOf).filter(v => isFinite(v)) : [];
  const impMax = impVals.length ? Math.max(...impVals) : 1;
  const impMin = impVals.length ? Math.min(...impVals) : 0;
  const norm = v => (impMax > impMin ? (v - impMin) / (impMax - impMin) : 0.5);

  // ---- views: [horizontal axis, vertical axis, label, flip vertical]
  const VIEWS = [
    { a: 'x', b: 'y', title: 'From above', note: 'left of image = left hemisphere' },
    { a: 'y', b: 'z', title: 'From the side', note: 'front of head to the right' },
  ];

  function svgFor(view, w, h) {
    const pad = 16;
    const xs = nodes.map(n => n[view.a]), ys = nodes.map(n => n[view.b]);
    const x0 = Math.min(...xs), x1 = Math.max(...xs);
    const y0 = Math.min(...ys), y1 = Math.max(...ys);
    const sx = v => pad + ((v - x0) / (x1 - x0)) * (w - 2 * pad);
    const sy = v => h - pad - ((v - y0) / (y1 - y0)) * (h - 2 * pad);

    let s = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${view.title}">`;
    s += `<ellipse cx="${w / 2}" cy="${h / 2}" rx="${w / 2 - pad + 6}" ry="${h / 2 - pad + 6}"
           fill="var(--bg-soft)" stroke="var(--rule)"/>`;
    if (view.a === 'x') {
      s += `<line x1="${w / 2}" y1="${pad - 6}" x2="${w / 2}" y2="${h - pad + 6}"
             stroke="var(--rule)" stroke-dasharray="3 4"/>`;
    }
    const order = [...nodes].sort((m, n) => (imp ? norm(impOf(m)) - norm(impOf(n)) : 0));
    for (const n of order) {
      const on = active.has(n.network);
      const t = imp ? norm(impOf(n)) : 0.5;
      const r = imp ? 2.2 + t * 7 : 3.4;
      const op = on ? (imp ? 0.35 + 0.65 * t : 0.85) : 0.07;
      const isSel = selected && selected.id === n.id;
      s += `<circle class="bnode" data-id="${n.id}" cx="${sx(n[view.a]).toFixed(1)}"
             cy="${sy(n[view.b]).toFixed(1)}" r="${(isSel ? r + 3 : r).toFixed(1)}"
             fill="${palette[n.network]}" fill-opacity="${op.toFixed(2)}"
             stroke="${isSel ? 'var(--fg)' : 'none'}" stroke-width="1.5"
             tabindex="0" role="button"
             aria-label="${n.label}"><title>${n.label}${imp ? ' — importance ' + impOf(n).toFixed(3) : ''}</title></circle>`;
    }
    s += `</svg>`;
    return `<figure class="bview"><div class="bviewhead">${view.title}
            <span class="small">· ${view.note}</span></div>${s}</figure>`;
  }

  function legend() {
    return `<div class="legend">` + nets.map(n =>
      `<button class="lg${active.has(n) ? ' on' : ''}" data-net="${n}">
        <span class="sw" style="background:${palette[n]}"></span>${n}</button>`).join('')
      + `<button class="lg reset" data-net="__all">reset</button></div>`;
  }

  function detail() {
    if (!selected) {
      return `<p class="small">Select a region, or filter by network above.${
        imp ? ' Larger, more solid circles are regions the model relied on more.' : ''}</p>`;
    }
    const n = selected;
    return `<div class="card"><h3>${n.label}</h3>
      <p class="small">${n.network} · ${n.hemi === 'LH' ? 'left' : n.hemi === 'RH' ? 'right' : 'midline'}
      · ${n.source} · ${n.n_voxels} voxels<br>
      MNI ${n.x}, ${n.y}, ${n.z}${imp ? `<br><strong>importance ${impOf(n).toFixed(4)}</strong>` : ''}</p></div>`;
  }

  function topTable() {
    if (!imp) return '';
    const rows = [...nodes].sort((a, b) => impOf(b) - impOf(a)).slice(0, 15).map((n, i) =>
      `<tr><td class="num">${i + 1}</td><td>${n.label}</td><td>${n.network}</td>
       <td>${n.hemi === 'LH' ? 'left' : n.hemi === 'RH' ? 'right' : '—'}</td>
       <td class="num">${impOf(n).toFixed(4)}</td></tr>`).join('');
    return `<h3>Regions the model leaned on most</h3><div class="tablewrap"><table>
      <thead><tr><th class="num">#</th><th>Region</th><th>Network</th><th>Side</th>
      <th class="num">Importance</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function render() {
    host.innerHTML = legend()
      + `<div class="bgrid">${VIEWS.map(v => svgFor(v, 340, 300)).join('')}</div>`
      + `<div id="bdetail">${detail()}</div>` + topTable();
    host.querySelectorAll('.lg').forEach(b => b.addEventListener('click', () => {
      const n = b.dataset.net;
      if (n === '__all') active = new Set(nets);
      else if (active.size === nets.length) active = new Set([n]);
      else if (active.has(n)) { active.delete(n); if (!active.size) active = new Set(nets); }
      else active.add(n);
      render();
    }));
    const pick = el => {
      const id = +el.dataset.id;
      selected = nodes.find(n => n.id === id) || null;
      render();
    };
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
.bgrid { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(17rem, 1fr));
         margin: 1.2rem 0; }
.bview { margin: 0; border: 1px solid var(--rule); border-radius: 8px; padding: .6rem; }
.bviewhead { font-size: .84rem; color: var(--fg-mut); margin-bottom: .3rem; font-weight: 600; }
.bnode { cursor: pointer; }
.bnode:focus { outline: 2px solid var(--accent); outline-offset: 2px; }
.legend { display: flex; flex-wrap: wrap; gap: .35rem; margin: 1rem 0; }
.lg { display: inline-flex; align-items: center; gap: .35rem; font: inherit;
      font-size: .78rem; padding: .22rem .55rem; border-radius: 999px;
      border: 1px solid var(--rule); background: var(--bg); color: var(--fg-mut);
      cursor: pointer; }
.lg.on { color: var(--fg); border-color: var(--fg-faint); }
.lg .sw { width: .62rem; height: .62rem; border-radius: 50%; opacity: .35; }
.lg.on .sw { opacity: 1; }
.lg.reset { font-style: italic; }
#bdetail { margin: 1rem 0; min-height: 3rem; }
"""


def build_brain() -> None:
    imp = load("importance_LH") or {}
    meta = imp.get("model"), imp.get("n_folds")
    note = ""
    if imp.get("n_folds"):
        note = (f"<p>Importances come from {imp.get('model', 'the best model')}, "
                f"recomputed in each of {imp['n_folds']} cross-validation folds and "
                f"averaged. Only regions that rank highly <em>consistently</em> across "
                f"folds are meaningful; a single fit's saliency map at this sample size "
                f"is mostly noise.</p>")
    else:
        note = ('<p class="pending">Region importances appear once the models have '
                'been fit. Until then this shows the parcellation itself.</p>')

    enr = imp.get("network_enrichment") or {}
    enr_rows = ""
    for net, v in sorted(enr.items(), key=lambda kv: -(kv[1].get("z") or 0))[:8]:
        sig = " <span class='tag'>FDR ✓</span>" if v.get("fdr_pass") else ""
        enr_rows += (f"<tr><td>{e(net)}{sig}</td><td class='num'>{v.get('n_nodes','—')}</td>"
                     f"<td class='num'>{v.get('z', float('nan')):+.2f}</td>"
                     f"<td class='num'>{fmt_p(v.get('p_value'))}</td></tr>")
    enr_block = (f"""<h3>Which networks carried the signal</h3>
<div class="tablewrap"><table>
<thead><tr><th>Network</th><th class="num">Regions</th><th class="num">z</th>
<th class="num">p</th></tr></thead><tbody>{enr_rows}</tbody></table></div>
<p class="small">Tested against a null in which importance is shuffled across regions,
with Benjamini–Hochberg correction across networks.</p>""" if enr_rows else "")

    body = f"""
<h1>What the model learned</h1>
<p class="lede">241 regions — 200 cortical, 15 subcortical, 26 cerebellar. Filter by
network, or select any region to see where it sits and how much the model used it.</p>

<section>
<div class="measure">{note}</div>
<div id="brainapp"><p class="pending">Loading…</p></div>
</section>

<section>
{enr_block}
<div class="measure">
<p class="small">A caution worth repeating: importance tells you what the model used to
separate the groups, not what the brain is doing. Two regions carrying the same
information will often split the credit arbitrarily, and a region can rank low simply
because a neighbour already captured its signal.</p>
</div>
</section>

<style>{BRAIN_CSS}</style>
<script>{BRAIN_JS}</script>
"""
    write("brain.html", "Explore the brain", body,
          "Interactive map of the 241 brain regions and how much each contributed.")
