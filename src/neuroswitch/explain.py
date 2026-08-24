"""What the model learned -- with stability as a first-class requirement.

A saliency map from a single fit is close to noise at this sample size, so
nothing here reports a single model's attributions.  Every score is recomputed
in each CV fold and rank-aggregated, and only features that rank highly
*consistently* survive.  Network-level claims are tested against a permutation
null rather than eyeballed.
"""
from __future__ import annotations

import numpy as np
import torch
from scipy.stats import rankdata


# ---------------------------------------------------------------- attributions
def gnn_node_attributions(model, idx, bundle, target: int = 1,
                          n_steps: int = 32) -> np.ndarray:
    """Integrated Gradients over node features -> (n_graphs, n_nodes)."""
    from captum.attr import IntegratedGradients
    from torch_geometric.loader import DataLoader

    graphs = model.graphs_for(idx, bundle)
    net = model.net
    net.eval()
    scores = []
    for batch in DataLoader(graphs, batch_size=1):
        x = batch.x.clone().requires_grad_(True)

        def fwd(inp, b=batch):
            return net(inp, b.edge_index, b.batch, b.edge_attr.squeeze(-1))

        ig = IntegratedGradients(fwd)
        att = ig.attribute(x, target=target, n_steps=n_steps,
                           baselines=torch.zeros_like(x))
        # one score per node: total absolute attribution across its features
        scores.append(att.abs().sum(dim=1).detach().cpu().numpy())
    return np.vstack(scores)


def gnn_edge_importance(model, idx, bundle, epochs: int = 100) -> np.ndarray:
    """GNNExplainer edge masks, averaged into a symmetric node-by-node matrix."""
    from torch_geometric.explain import Explainer, GNNExplainer
    from torch_geometric.loader import DataLoader

    graphs = model.graphs_for(idx, bundle)
    n = graphs[0].num_nodes

    class _Wrap(torch.nn.Module):
        def __init__(self, net): super().__init__(); self.net = net
        def forward(self, x, edge_index, **kw):
            batch = kw.get("batch")
            if batch is None:
                batch = torch.zeros(x.size(0), dtype=torch.long, device=x.device)
            return self.net(x, edge_index, batch)

    ex = Explainer(model=_Wrap(model.net), algorithm=GNNExplainer(epochs=epochs),
                   explanation_type="model", edge_mask_type="object",
                   node_mask_type="object",
                   model_config=dict(mode="multiclass_classification",
                                     task_level="graph", return_type="raw"))
    acc = np.zeros((n, n), dtype=np.float64)
    cnt = 0
    for batch in DataLoader(graphs, batch_size=1):
        try:
            e = ex(batch.x, batch.edge_index, batch=batch.batch)
        except Exception:
            continue
        m = e.edge_mask.detach().cpu().numpy()
        src, dst = batch.edge_index.cpu().numpy()
        mat = np.zeros((n, n))
        mat[src, dst] = m
        acc += (mat + mat.T) / 2.0
        cnt += 1
    return acc / max(cnt, 1)


def linear_edge_importance(model, n_nodes: int) -> np.ndarray:
    """Map a linear classifier's edge coefficients back to a node-by-node matrix.

    When a linear model on connectivity edges is the best performer -- which is
    common at this sample size -- these coefficients *are* the interpretability
    result, and are far more stable than GNN saliency.
    """
    clf = model.pipe.named_steps["clf"]
    coef = np.ravel(clf.coef_ if hasattr(clf, "coef_") else clf.dual_coef_)
    good = np.flatnonzero(model.conn.good)
    k = len(good)
    mat = np.zeros((n_nodes, n_nodes))
    iu = np.triu_indices(k, k=1)
    if coef.size == iu[0].size:                       # discard_diagonal=True
        sub = np.zeros((k, k)); sub[iu] = coef
    else:                                             # diagonal retained
        iu2 = np.triu_indices(k, k=0)
        sub = np.zeros((k, k)); sub[iu2] = coef[:iu2[0].size]
    sub = sub + sub.T
    mat[np.ix_(good, good)] = sub
    return mat


# ------------------------------------------------------------------ stability
def stability_rank_aggregate(score_list: list[np.ndarray]) -> dict[str, np.ndarray]:
    """Aggregate per-fold scores by mean rank; report how often each ranks top-10%."""
    s = np.vstack([np.nan_to_num(np.asarray(x, dtype=float).ravel()) for x in score_list])
    ranks = np.vstack([rankdata(-row) for row in s])      # rank 1 = most important
    mean_rank = ranks.mean(0)
    top_k = max(1, int(round(0.10 * s.shape[1])))
    selection_freq = (ranks <= top_k).mean(0)
    return {"mean_rank": mean_rank, "selection_frequency": selection_freq,
            "mean_score": s.mean(0), "sd_score": s.std(0), "n_folds": s.shape[0]}


def stable_set(agg: dict[str, np.ndarray], min_freq: float = 0.80) -> np.ndarray:
    return np.flatnonzero(agg["selection_frequency"] >= min_freq)


# ----------------------------------------------------------------- enrichment
def network_enrichment(scores: np.ndarray, networks: list[str], n_perm: int = 10000,
                       seed: int = 0) -> dict[str, dict]:
    """Is a network's mean importance higher than chance, given the node scores?"""
    scores = np.nan_to_num(np.asarray(scores, dtype=float))
    nets = np.asarray(networks)
    rng = np.random.RandomState(seed)
    out = {}
    for net in sorted(set(nets)):
        m = nets == net
        obs = float(scores[m].mean())
        null = np.array([scores[rng.permutation(len(scores))][m].mean()
                         for _ in range(n_perm)])
        p = float((np.sum(null >= obs) + 1) / (n_perm + 1))
        out[net] = {"n_nodes": int(m.sum()), "observed_mean": obs,
                    "null_mean": float(null.mean()), "null_sd": float(null.std()),
                    "p_value": p,
                    "z": float((obs - null.mean()) / (null.std() + 1e-12))}
    return out


def fdr(pvals: dict[str, float], q: float = 0.05) -> dict[str, bool]:
    """Benjamini-Hochberg across the network tests."""
    keys = list(pvals)
    p = np.array([pvals[k] for k in keys], dtype=float)
    order = np.argsort(p)
    m = len(p)
    thresh = (np.arange(1, m + 1) / m) * q
    passed = p[order] <= thresh
    cut = np.max(np.flatnonzero(passed)) if passed.any() else -1
    keep = set(np.array(keys)[order][:cut + 1]) if cut >= 0 else set()
    return {k: (k in keep) for k in keys}
