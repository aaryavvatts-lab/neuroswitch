"""Run enumeration must survive reaping.

The reaper deletes raw NIfTIs once derivatives are verified.  Anything that
enumerates a subject's runs by globbing the raw BIDS tree therefore reports zero
runs for every completed subject -- silently producing empty features rather
than failing.  These tests pin the derivative-based behaviour.
"""
import numpy as np
import pytest

from neuroswitch import run_subject as rs


@pytest.fixture
def fake_derivatives(tmp_path, monkeypatch):
    deriv = tmp_path / "derivatives"
    (deriv / "sub-9001").mkdir(parents=True)
    for task, runs in (("drawLH", (1, 2, 3)), ("drawRH", (1, 2))):
        for r in runs:
            np.savez(deriv / "sub-9001" / f"sub-9001_task-{task}_run-{r}.npz",
                     ts=np.zeros((10, 4), dtype=np.float32))
    monkeypatch.setattr(rs, "DERIV", deriv)
    return deriv


def test_derivative_runs_found_without_any_raw_data(fake_derivatives, tmp_path, monkeypatch):
    """No raw BIDS tree at all -- enumeration must still work."""
    from neuroswitch import preprocess as pp
    monkeypatch.setattr(pp, "BIDS", tmp_path / "does_not_exist")
    assert rs.available_runs("sub-9001", "drawLH") == []      # raw view sees nothing
    assert rs.derivative_runs("sub-9001", "drawLH") == [1, 2, 3]
    assert rs.derivative_runs("sub-9001", "drawRH") == [1, 2]


def test_derivative_runs_empty_for_unknown_subject(fake_derivatives):
    assert rs.derivative_runs("sub-9999", "drawLH") == []


def test_derivative_runs_ignores_other_tasks(fake_derivatives):
    assert rs.derivative_runs("sub-9001", "restingstate") == []


def test_features_usable_reads_derivatives_not_raw(fake_derivatives, monkeypatch):
    """_usable must consult derivative_runs, so reaped subjects still build."""
    import json
    from neuroswitch import features as F
    monkeypatch.setattr(F, "DERIV", fake_derivatives)
    monkeypatch.setattr(F, "derivative_runs", rs.derivative_runs)
    for r in (1, 2, 3):
        (fake_derivatives / "sub-9001" / f"sub-9001_task-drawLH_run-{r}_qc.json").write_text(
            json.dumps({"mean_fd": 0.1, "pct_censored": 1.0, "reg_dice_mni_to_epi": 0.95}))
    assert F._usable("sub-9001", "drawLH") == [1, 2, 3]


def test_features_usable_applies_qc_thresholds(fake_derivatives, monkeypatch):
    import json
    from neuroswitch import features as F
    monkeypatch.setattr(F, "DERIV", fake_derivatives)
    monkeypatch.setattr(F, "derivative_runs", rs.derivative_runs)
    qc = [{"mean_fd": 0.1, "pct_censored": 1.0, "reg_dice_mni_to_epi": 0.95},   # ok
          {"mean_fd": 0.9, "pct_censored": 1.0, "reg_dice_mni_to_epi": 0.95},   # motion
          {"mean_fd": 0.1, "pct_censored": 1.0, "reg_dice_mni_to_epi": 0.10}]   # registration
    for r, q in zip((1, 2, 3), qc):
        (fake_derivatives / "sub-9001" / f"sub-9001_task-drawLH_run-{r}_qc.json").write_text(
            json.dumps(q))
    assert F._usable("sub-9001", "drawLH") == [1]
