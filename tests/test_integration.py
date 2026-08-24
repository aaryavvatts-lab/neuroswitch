"""Dress rehearsal for the full analysis chain.

The real run takes many hours, so every model, the permutation machinery, the
control analyses and the site build are exercised here on synthetic bundles
whose ground truth is known.  Catches integration breakage now instead of after
an overnight preprocessing run.
"""
import numpy as np
import pytest

from neuroswitch.validate import Bundle, cross_validate, permutation_test


def make_bundle(n=32, n_nodes=18, n_t=140, effect=0.9, seed=0, paired=False):
    rng = np.random.RandomState(seed)
    y = np.array([0] * (n // 2) + [1] * (n - n // 2))
    subs = np.array([f"sub-{9000+i}" for i in range(n)])
    ts, pair = [], []
    for i in range(n):
        trait = rng.randn(n_t, 1) * 1.2          # subject-level, present in both conditions
        a = rng.randn(n_t, n_nodes) + trait
        if y[i]:
            a[:, :4] += effect * a[:, 4:8]       # group effect, condition A only
        ts.append(a.astype(np.float32))
        pair.append((rng.randn(n_t, n_nodes) + trait).astype(np.float32))
    tables = {
        "motion": rng.randn(n, 2),
        "behaviour": np.column_stack([y * 1.6 + rng.randn(n) * 0.9, rng.randn(n, 3)]),
        "behaviour_lh": np.column_stack([y * 1.6 + rng.randn(n) * 0.9, rng.randn(n, 3)]),
        "demographics": rng.randn(n, 3),
    }
    meta = {"network_onehot": np.eye(n_nodes, dtype=np.float32)}
    if paired:
        meta["ts_pair"] = pair
    return Bundle(ts=ts, y=y, subs=subs, tables=tables, node_meta=meta)


def test_every_model_in_the_suite_runs():
    from neuroswitch.experiments import model_suite
    b = make_bundle()
    suite = model_suite(include_gnn=True)
    assert {"GCN", "tangent+logreg", "NULL motion-only",
            "NULL behaviour-only"} <= set(suite)
    for name, make in suite.items():
        r = cross_validate(make, b, n_splits=4, n_repeats=1)
        assert np.isfinite(r["auc_mean"]), f"{name} produced no AUC"
        assert 0.0 <= r["auc_mean"] <= 1.0


def test_signal_is_found_and_pure_noise_is_not():
    signal = cross_validate(lambda: _lin(), make_bundle(effect=1.0), n_splits=4, n_repeats=2)
    noise = cross_validate(lambda: _lin(), make_bundle(effect=0.0, seed=7),
                           n_splits=4, n_repeats=2)
    assert signal["auc_mean"] > 0.75, signal["auc_mean"]
    assert noise["auc_mean"] < 0.75, noise["auc_mean"]


def _lin():
    from neuroswitch.models.baselines import ConnEdgeModel
    return ConnEdgeModel("tangent", "logreg")


def test_permutation_null_centres_on_chance():
    """If the null does not sit near 0.5 the cross-validation is leaking."""
    b = make_bundle(effect=1.0)
    pt = permutation_test(_lin, b, n_perm=40, n_splits=4)
    assert 0.35 < pt["null_mean"] < 0.65, pt["null_mean"]
    assert 0.0 < pt["p_value"] <= 1.0
    assert pt["p_value"] >= 1 / (pt["n_perm"] + 1)      # +1 correction applied


def test_difference_graph_cancels_a_subject_level_trait():
    from neuroswitch.models.paired import DiffConnEdgeModel
    b = make_bundle(paired=True, effect=1.0)
    r = cross_validate(lambda: DiffConnEdgeModel("tangent"), b, n_splits=4, n_repeats=1)
    assert r["auc_mean"] > 0.7, r["auc_mean"]


def test_residualising_a_confound_removes_a_confound_only_effect():
    """A bundle whose ONLY group signal is the confound must collapse to chance."""
    from neuroswitch.models.paired import ResidualizedConnModel
    from neuroswitch.models.baselines import TableModel
    b = make_bundle(effect=0.0, seed=11)               # no brain effect at all
    beh = cross_validate(lambda: TableModel("behaviour_lh"), b, n_splits=4, n_repeats=2)
    assert beh["auc_mean"] > 0.7                        # behaviour alone does separate
    resid = cross_validate(lambda: ResidualizedConnModel("behaviour_lh"), b,
                           n_splits=4, n_repeats=2)
    assert resid["auc_mean"] < 0.75, resid["auc_mean"]  # brain adds nothing real


def test_importance_recovers_the_regions_carrying_the_effect():
    from neuroswitch.explain import stability_rank_aggregate
    from neuroswitch.run_importance import node_scores_linear
    from sklearn.model_selection import StratifiedGroupKFold
    b = make_bundle(effect=1.2, n_nodes=18)
    folds = []
    cv = StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=0)
    for tr, _ in cv.split(np.zeros(len(b)), b.y, b.subs):
        folds.append(node_scores_linear(_lin().fit(tr, b), 18))
    agg = stability_rank_aggregate(folds)
    top8 = set(np.argsort(-agg["mean_score"])[:8])
    planted = set(range(8))                             # nodes 0-7 carry the effect
    assert len(top8 & planted) >= 5, sorted(top8)


def test_site_builds_with_no_results_present(tmp_path, monkeypatch):
    """The site must stay buildable throughout a long pipeline run."""
    from neuroswitch import site_build
    monkeypatch.setattr(site_build, "RESULTS", tmp_path / "empty")
    monkeypatch.setattr(site_build, "SITE", tmp_path / "site")
    import neuroswitch.pages as pages
    monkeypatch.setattr(pages, "load", lambda name: None)
    for fn in (pages.build_index, pages.build_data, pages.build_methods,
               pages.build_results, pages.build_brain, pages.build_controls,
               pages.build_reproduce, pages.build_refs):
        fn()
    made = sorted(p.name for p in (tmp_path / "site").glob("*.html"))
    assert len(made) == 8, made
    for p in (tmp_path / "site").glob("*.html"):
        t = p.read_text()
        assert t.startswith("<!doctype html>") and t.rstrip().endswith("</html>")
        assert "{" not in t.split("<body>")[1][:200]     # no unrendered f-string braces
