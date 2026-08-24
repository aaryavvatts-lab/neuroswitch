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


def test_reap_refuses_when_a_file_is_not_recoverable(tmp_path, monkeypatch):
    """Deletion must be blocked unless every file can be fetched again.

    The local manifest only lists files present when it was written, so subjects
    downloaded later are absent from it. Those are checked against the public
    bucket instead. If neither source confirms the file, nothing is deleted.
    """
    import json
    import numpy as np
    from neuroswitch import reap as R

    bids = tmp_path / "bids"
    deriv = tmp_path / "derivatives"
    (bids / "sub-9001" / "func").mkdir(parents=True)
    (deriv / "sub-9001").mkdir(parents=True)
    monkeypatch.setattr(R, "BIDS", bids)
    monkeypatch.setattr(R, "DERIV", deriv)

    raw = bids / "sub-9001" / "func" / "sub-9001_task-drawLH_run-1_bold.nii.gz"
    raw.write_bytes(b"x" * 2048)
    rng = np.random.RandomState(0)
    np.savez(deriv / "sub-9001" / "sub-9001_task-drawLH_run-1.npz",
             ts=rng.randn(300, 4).astype(np.float32), cover=np.full(4, 50))
    (deriv / "sub-9001" / "subject_qc.json").write_text(json.dumps(
        {"status": "complete", "n_failed": 0, "failures": [],
         "runs": [{"task": "drawLH", "run": 1, "reg_dice_mni_to_epi": 0.96}]}))
    monkeypatch.setattr(R, "available_runs", lambda s, t: [1] if t == "drawLH" else [])
    monkeypatch.setattr(R, "derivative_runs", lambda s, t: [1] if t == "drawLH" else [])

    # nothing in the manifest, and the bucket does not confirm it
    monkeypatch.setattr(R, "_manifest_index", lambda: {})
    monkeypatch.setattr(R, "_remote_size", lambda rel, timeout=30: None)
    r = R.reap("sub-9001", dry_run=False, expect_nodes=4, tasks=("drawLH",))
    assert not r["reaped"] and raw.is_file(), "deleted a file it could not restore"

    # bucket confirms a different size: still refuse
    monkeypatch.setattr(R, "_remote_size", lambda rel, timeout=30: 999)
    r = R.reap("sub-9001", dry_run=False, expect_nodes=4, tasks=("drawLH",))
    assert not r["reaped"] and raw.is_file(), "size mismatch should block deletion"

    # bucket confirms the exact size: now it may go
    monkeypatch.setattr(R, "_remote_size", lambda rel, timeout=30: 2048)
    r = R.reap("sub-9001", dry_run=False, expect_nodes=4, tasks=("drawLH",))
    assert r["reaped"] and not raw.is_file()


def test_reap_refuses_when_derivatives_look_wrong(tmp_path, monkeypatch):
    import json
    import numpy as np
    from neuroswitch import reap as R

    bids = tmp_path / "bids"
    deriv = tmp_path / "derivatives"
    (bids / "sub-9002" / "func").mkdir(parents=True)
    (deriv / "sub-9002").mkdir(parents=True)
    monkeypatch.setattr(R, "BIDS", bids)
    monkeypatch.setattr(R, "DERIV", deriv)
    raw = bids / "sub-9002" / "func" / "sub-9002_task-drawLH_run-1_bold.nii.gz"
    raw.write_bytes(b"x" * 2048)
    monkeypatch.setattr(R, "available_runs", lambda s, t: [1] if t == "drawLH" else [])
    monkeypatch.setattr(R, "derivative_runs", lambda s, t: [1] if t == "drawLH" else [])
    monkeypatch.setattr(R, "_manifest_index", lambda: {"sub-9002/func/sub-9002_task-drawLH_run-1_bold.nii.gz": 2048})

    # a time series that is all NaN must block deletion
    np.savez(deriv / "sub-9002" / "sub-9002_task-drawLH_run-1.npz",
             ts=np.full((300, 4), np.nan, dtype=np.float32), cover=np.full(4, 50))
    (deriv / "sub-9002" / "subject_qc.json").write_text(json.dumps(
        {"status": "complete", "n_failed": 0, "failures": [],
         "runs": [{"task": "drawLH", "run": 1, "reg_dice_mni_to_epi": 0.96}]}))
    r = R.reap("sub-9002", dry_run=False, expect_nodes=4, tasks=("drawLH",))
    assert not r["reaped"] and raw.is_file()

    # bad registration must also block it
    np.savez(deriv / "sub-9002" / "sub-9002_task-drawLH_run-1.npz",
             ts=np.random.RandomState(1).randn(300, 4).astype(np.float32),
             cover=np.full(4, 50))
    (deriv / "sub-9002" / "subject_qc.json").write_text(json.dumps(
        {"status": "complete", "n_failed": 0, "failures": [],
         "runs": [{"task": "drawLH", "run": 1, "reg_dice_mni_to_epi": 0.20}]}))
    r = R.reap("sub-9002", dry_run=False, expect_nodes=4, tasks=("drawLH",))
    assert not r["reaped"] and raw.is_file()


def test_reap_refuses_a_flat_time_series(tmp_path, monkeypatch):
    """A constant signal means extraction silently produced nothing usable."""
    import json
    import numpy as np
    from neuroswitch import reap as R

    bids, deriv = tmp_path / "bids", tmp_path / "derivatives"
    (bids / "sub-9003" / "func").mkdir(parents=True)
    (deriv / "sub-9003").mkdir(parents=True)
    monkeypatch.setattr(R, "BIDS", bids)
    monkeypatch.setattr(R, "DERIV", deriv)
    raw = bids / "sub-9003" / "func" / "sub-9003_task-drawLH_run-1_bold.nii.gz"
    raw.write_bytes(b"x" * 2048)
    monkeypatch.setattr(R, "available_runs", lambda s, t: [1] if t == "drawLH" else [])
    monkeypatch.setattr(R, "derivative_runs", lambda s, t: [1] if t == "drawLH" else [])
    monkeypatch.setattr(R, "_manifest_index", lambda: {
        "sub-9003/func/sub-9003_task-drawLH_run-1_bold.nii.gz": 2048})
    np.savez(deriv / "sub-9003" / "sub-9003_task-drawLH_run-1.npz",
             ts=np.ones((300, 4), dtype=np.float32), cover=np.full(4, 50))
    (deriv / "sub-9003" / "subject_qc.json").write_text(json.dumps(
        {"status": "complete", "n_failed": 0, "failures": [],
         "runs": [{"task": "drawLH", "run": 1, "reg_dice_mni_to_epi": 0.96}]}))
    r = R.reap("sub-9003", dry_run=False, expect_nodes=4, tasks=("drawLH",))
    assert not r["reaped"] and raw.is_file()
    assert any("zero variance" in x for x in r["reasons"]), r["reasons"]
