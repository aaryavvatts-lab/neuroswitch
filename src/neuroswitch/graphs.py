"""Connectivity estimation and graph construction.

Estimators that pool information across subjects (tangent-space embedding) are
written as fit/transform objects so a caller can fit on the training split
only.  Estimators that are purely within-subject (correlation, partial
correlation) go through the same interface for uniformity.
"""
from __future__ import annotations

import numpy as np
from nilearn.connectome import ConnectivityMeasure, sym_matrix_to_vec
from sklearn.covariance import LedoitWolf


def _sanitize(ts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Drop all-NaN parcels; return the cleaned series and the kept-column mask."""
    good = ~np.isnan(ts).any(axis=0)
    return ts[:, good], good


class Connectivity:
    """Wraps nilearn's ConnectivityMeasure with explicit fit/transform.

    ``kind='tangent'`` learns a group mean covariance and MUST be fit on
    training subjects only.  The other kinds are subject-independent, but share
    this interface so that the CV code never has to special-case them.
    """

    def __init__(self, kind: str = "partial correlation", n_nodes: int | None = None):
        self.kind = kind
        self.n_nodes = n_nodes
        self._cm = None
        self._good: np.ndarray | None = None

    @staticmethod
    def _common_good(ts_list: list[np.ndarray]) -> np.ndarray:
        """Parcels usable in every subject -- connectivity needs a shared node set."""
        return ~np.stack([np.isnan(t).any(0) for t in ts_list]).any(0)

    def fit(self, ts_list: list[np.ndarray]) -> "Connectivity":
        self._good = self._common_good(ts_list)
        self.n_nodes = self.n_nodes or ts_list[0].shape[1]
        est = LedoitWolf(store_precision=False, assume_centered=False)
        self._cm = ConnectivityMeasure(kind=self.kind, cov_estimator=est,
                                       standardize="zscore_sample")
        self._cm.fit([t[:, self._good] for t in ts_list])
        return self

    def transform(self, ts_list: list[np.ndarray]) -> np.ndarray:
        """-> (n_subjects, n_nodes, n_nodes) with dropped parcels reinstated as NaN."""
        mats = self._cm.transform([t[:, self._good] for t in ts_list])
        n = self.n_nodes
        out = np.full((len(ts_list), n, n), np.nan, dtype=np.float32)
        idx = np.flatnonzero(self._good)
        for k, m in enumerate(mats):
            out[k][np.ix_(idx, idx)] = m
        return out

    def fit_transform(self, ts_list: list[np.ndarray]) -> np.ndarray:
        return self.fit(ts_list).transform(ts_list)

    @property
    def good(self) -> np.ndarray:
        return self._good


def fisher_z(mat: np.ndarray) -> np.ndarray:
    m = np.clip(mat, -0.999999, 0.999999)
    return np.arctanh(m)


def vectorize(mats: np.ndarray, discard_diagonal: bool = True) -> np.ndarray:
    """Upper triangle of each matrix, NaNs -> 0."""
    out = []
    for m in mats:
        v = sym_matrix_to_vec(np.nan_to_num(m, nan=0.0),
                              discard_diagonal=discard_diagonal)
        out.append(v)
    return np.asarray(out, dtype=np.float32)


def threshold_topk(mat: np.ndarray, density: float = 0.10) -> np.ndarray:
    """Keep the strongest |edges| at the given density; sign is preserved."""
    n = mat.shape[0]
    m = np.nan_to_num(mat, nan=0.0).copy()
    np.fill_diagonal(m, 0.0)
    iu = np.triu_indices(n, k=1)
    vals = np.abs(m[iu])
    k = max(1, int(round(density * vals.size)))
    if k >= vals.size:
        thresh = -np.inf
    else:
        thresh = np.partition(vals, -k)[-k]
    keep = np.abs(m) >= thresh
    keep &= ~np.eye(n, dtype=bool)
    out = np.where(keep, m, 0.0)
    return (out + out.T) / 2.0          # re-symmetrise after thresholding


def graph_metrics(mat: np.ndarray, density: float = 0.10) -> dict[str, np.ndarray]:
    """Classic graph-theory summaries used by the non-deep baseline."""
    import networkx as nx
    a = threshold_topk(mat, density)
    w = np.abs(a)
    g = nx.from_numpy_array(w)
    strength = w.sum(1)
    clus = np.array(list(nx.clustering(g, weight="weight").values()))
    btw = np.array(list(nx.betweenness_centrality(g, weight=None).values()))
    return {"strength": strength, "clustering": clus, "betweenness": btw,
            "global_efficiency": np.array([nx.global_efficiency(g)])}


def to_pyg(mat: np.ndarray, node_feat: np.ndarray, y: int, density: float = 0.10,
           sub: str = "", cond: str = ""):
    """One brain -> one torch_geometric graph."""
    import torch
    from torch_geometric.data import Data

    a = threshold_topk(mat, density)
    src, dst = np.nonzero(a)
    edge_index = torch.tensor(np.vstack([src, dst]), dtype=torch.long)
    edge_attr = torch.tensor(a[src, dst], dtype=torch.float).unsqueeze(1)
    x = torch.tensor(np.nan_to_num(node_feat, nan=0.0), dtype=torch.float)
    d = Data(x=x, edge_index=edge_index, edge_attr=edge_attr,
             y=torch.tensor([y], dtype=torch.long))
    d.sub, d.cond = sub, cond
    return d


def node_features(mat: np.ndarray, extra: dict[str, np.ndarray] | None = None,
                  network_onehot: np.ndarray | None = None) -> np.ndarray:
    """Connectivity profile row, plus optional per-parcel scalars and network id."""
    prof = np.nan_to_num(fisher_z(mat), nan=0.0)
    parts = [prof]
    if extra:
        for _, v in sorted(extra.items()):
            col = np.nan_to_num(np.asarray(v, dtype=np.float32), nan=0.0)
            sd = col.std()
            parts.append(((col - col.mean()) / (sd + 1e-8)).reshape(-1, 1))
    if network_onehot is not None:
        parts.append(network_onehot)
    return np.hstack(parts).astype(np.float32)
