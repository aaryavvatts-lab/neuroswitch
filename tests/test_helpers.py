import numpy as np
import pytest
from neuroswitch.preprocess import (slice_time_correct, friston24, dvars, compcor,
                                    dice, rigid_params_from_mat)


def test_slice_time_correct_is_exact_for_a_commensurate_signal():
    """When the signal is periodic in the window the Fourier shift is exact."""
    n_t, tr, cycles, off = 128, 0.662, 8, 0.45      # off in samples
    t = np.arange(n_t)
    arr = np.zeros((1, 1, 2, n_t), dtype=np.float32)
    arr[:, :, 0, :] = np.sin(2 * np.pi * cycles * t / n_t)
    arr[:, :, 1, :] = np.sin(2 * np.pi * cycles * (t + off) / n_t)
    out = slice_time_correct(arr, [0.0, off * tr], tr, pad=0)
    assert np.max(np.abs(out[0, 0, 0] - out[0, 0, 1])) < 1e-5


def test_slice_time_correct_removes_most_of_a_realistic_offset():
    """Real runs are not periodic; require a large reduction, not exactness."""
    n_t, tr, freq, off = 478, 0.662, 0.033, 0.578   # block rate; our largest slice offset
    t = np.arange(n_t) * tr
    arr = np.zeros((1, 1, 2, n_t), dtype=np.float32)
    arr[:, :, 0, :] = np.sin(2 * np.pi * freq * t)
    arr[:, :, 1, :] = np.sin(2 * np.pi * freq * (t + off))
    before = np.max(np.abs(arr[0, 0, 0, 20:-20] - arr[0, 0, 1, 20:-20]))
    out = slice_time_correct(arr, [0.0, off], tr)
    after = np.max(np.abs(out[0, 0, 0, 20:-20] - out[0, 0, 1, 20:-20]))
    assert before > 0.1                              # the offset really mattered
    assert after < before / 50                       # and is now negligible vs BOLD (1-3%)


def test_slice_time_correct_is_identity_at_zero_offset():
    arr = np.random.RandomState(0).randn(2, 2, 3, 64).astype(np.float32)
    out = slice_time_correct(arr.copy(), [0.0, 0.0, 0.0], 0.662)
    assert np.allclose(arr, out)


def test_friston24_shape_and_content():
    m = np.random.RandomState(1).randn(50, 6)
    f = friston24(m)
    assert f.shape == (50, 24)
    assert np.allclose(f[:, :6], m)
    assert np.allclose(f[:, 12:18], m ** 2)
    assert np.allclose(f[0, 6:12], 0.0)           # first derivative row is zero-padded


def test_dvars_zero_for_constant_series():
    data = np.ones((4, 4, 4, 20), dtype=np.float32)
    mask = np.ones((4, 4, 4), dtype=bool)
    assert np.allclose(dvars(data, mask), 0.0)


def test_dvars_detects_a_single_jump():
    data = np.ones((4, 4, 4, 10), dtype=np.float32)
    data[..., 5:] = 2.0
    dv = dvars(data, np.ones((4, 4, 4), dtype=bool))
    assert dv.argmax() == 5 and dv[5] > 10


def test_compcor_recovers_a_dominant_noise_signal():
    rng = np.random.RandomState(2)
    n_t = 100
    source = np.sin(np.linspace(0, 8 * np.pi, n_t))
    data = np.zeros((5, 5, 5, n_t), dtype=np.float32)
    mask = np.zeros((5, 5, 5), dtype=bool); mask[:3, :3, :3] = True
    data[mask] = 100.0 + 10.0 * source + 0.01 * rng.randn(mask.sum(), n_t)
    comps = compcor(data, mask, n_comp=3)
    assert comps.shape == (n_t, 3)
    r = abs(np.corrcoef(comps[:, 0], source)[0, 1])
    assert r > 0.95, r


def test_dice_bounds():
    a = np.zeros(100, bool); a[:50] = True
    assert dice(a, a) == 1.0
    assert dice(a, ~a) == 0.0


def test_rigid_params_roundtrip(tmp_path):
    """A known rotation+translation must decompose back to itself."""
    import ants
    tx = ants.create_ants_transform(transform_type="AffineTransform", dimension=3)
    ang = 0.03
    rot = np.array([[np.cos(ang), -np.sin(ang), 0],
                    [np.sin(ang),  np.cos(ang), 0],
                    [0, 0, 1.0]])
    trans = np.array([1.5, -2.0, 0.75])
    tx.set_parameters(np.concatenate([rot.ravel(), trans]))
    p = tmp_path / "t.mat"
    ants.write_transform(tx, str(p))
    got = rigid_params_from_mat(str(p))
    assert np.allclose(got[:3], trans, atol=1e-5)
    assert np.allclose(got[5], ang, atol=1e-5)       # rz
    assert np.allclose(got[3:5], 0.0, atol=1e-5)
