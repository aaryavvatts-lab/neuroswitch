"""Graph neural networks over subject connectomes.

The reel asks for a GCN, so GCN is here -- but at n~66 a deep model on ~241
nodes overfits readily, so training is deliberately conservative: an inner
validation split with early stopping, class-balanced loss, dropout, and weight
decay.  GAT/GIN are included as stronger comparators, and a top-k pooling
variant provides node-level importances directly.
"""
from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.loader import DataLoader
from torch_geometric.nn import (GATv2Conv, GCNConv, GINConv, global_max_pool,
                                global_mean_pool)
from sklearn.model_selection import StratifiedGroupKFold

from ..graphs import Connectivity, node_features, to_pyg
from ..validate import Bundle


def set_seed(s: int) -> None:
    torch.manual_seed(s)
    np.random.seed(s)


class BrainGNN(nn.Module):
    def __init__(self, in_dim: int, hidden: int = 64, n_layers: int = 2,
                 conv: str = "gcn", dropout: float = 0.5, heads: int = 4):
        super().__init__()
        self.convs, self.bns = nn.ModuleList(), nn.ModuleList()
        d = in_dim
        for _ in range(n_layers):
            if conv == "gcn":
                self.convs.append(GCNConv(d, hidden))
            elif conv == "gat":
                self.convs.append(GATv2Conv(d, hidden // heads, heads=heads))
            elif conv == "gin":
                self.convs.append(GINConv(nn.Sequential(
                    nn.Linear(d, hidden), nn.ReLU(), nn.Linear(hidden, hidden))))
            else:
                raise ValueError(conv)
            self.bns.append(nn.BatchNorm1d(hidden))
            d = hidden
        self.dropout = dropout
        self.head = nn.Sequential(
            nn.Linear(hidden * 2, hidden), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(hidden, 2))

    def forward(self, x, edge_index, batch, edge_weight=None):
        for conv, bn in zip(self.convs, self.bns):
            x = conv(x, edge_index, edge_weight) if isinstance(conv, GCNConv) \
                else conv(x, edge_index)
            x = F.relu(bn(x))
            x = F.dropout(x, p=self.dropout, training=self.training)
        self.node_embed = x
        g = torch.cat([global_mean_pool(x, batch), global_max_pool(x, batch)], dim=1)
        return self.head(g)


class GNNModel:
    """Full pipeline: time series -> connectivity (fit on train) -> graphs -> GNN."""

    def __init__(self, conv: str = "gcn", kind: str = "partial correlation",
                 density: float = 0.10, hidden: int = 64, n_layers: int = 2,
                 dropout: float = 0.5, lr: float = 1e-3, weight_decay: float = 5e-4,
                 epochs: int = 200, patience: int = 30, batch_size: int = 16,
                 seed: int = 0, use_extra_features: bool = True,
                 name: str | None = None):
        self.__dict__.update(locals()); del self.self
        self.name = name or f"{conv.upper()}"
        self.device = torch.device("cpu")      # graphs are tiny; CPU avoids MPS quirks

    # -- graph construction ------------------------------------------------
    def _extra(self, b: Bundle, i: int) -> dict:
        if not self.use_extra_features:
            return {}
        out = {}
        for key in ("beta_draw", "beta_hard_minus_easy", "alff", "falff"):
            arr = b.tables.get(key)
            if arr is not None:
                out[key] = arr[i]
        return out

    def _graphs(self, idx, b: Bundle, mats):
        onehot = b.node_meta.get("network_onehot")
        return [to_pyg(mats[k], node_features(mats[k], self._extra(b, i), onehot),
                       int(b.y[i]), self.density, sub=str(b.subs[i]))
                for k, i in enumerate(idx)]

    # -- training ----------------------------------------------------------
    def fit(self, idx, b: Bundle):
        set_seed(self.seed)
        idx = np.asarray(idx)
        ts_tr = [b.ts[i] for i in idx]
        self.conn = Connectivity(kind=self.kind, n_nodes=b.ts[0].shape[1]).fit(ts_tr)
        graphs = self._graphs(idx, b, self.conn.transform(ts_tr))

        # inner split for early stopping, still grouped by subject
        y_tr, g_tr = b.y[idx], b.subs[idx]
        inner = StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=self.seed)
        tr_i, va_i = next(iter(inner.split(np.zeros(len(idx)), y_tr, g_tr)))
        train_g = [graphs[i] for i in tr_i]
        val_g = [graphs[i] for i in va_i]

        self.net = BrainGNN(graphs[0].x.shape[1], self.hidden, self.n_layers,
                            self.conv, self.dropout).to(self.device)
        opt = torch.optim.Adam(self.net.parameters(), lr=self.lr,
                               weight_decay=self.weight_decay)
        counts = np.bincount(y_tr[tr_i], minlength=2).astype(float)
        w = torch.tensor((counts.sum() / (2 * np.maximum(counts, 1))), dtype=torch.float)
        lossf = nn.CrossEntropyLoss(weight=w.to(self.device))

        loader = DataLoader(train_g, batch_size=self.batch_size, shuffle=True)
        val_loader = DataLoader(val_g, batch_size=len(val_g) or 1)
        best, best_state, bad = np.inf, None, 0
        for _ in range(self.epochs):
            self.net.train()
            for batch in loader:
                batch = batch.to(self.device)
                opt.zero_grad()
                out = self.net(batch.x, batch.edge_index, batch.batch,
                               batch.edge_attr.squeeze(-1))
                loss = lossf(out, batch.y)
                loss.backward()
                nn.utils.clip_grad_norm_(self.net.parameters(), 1.0)
                opt.step()
            self.net.eval()
            with torch.no_grad():
                vl = 0.0
                for batch in val_loader:
                    batch = batch.to(self.device)
                    vl += float(lossf(self.net(batch.x, batch.edge_index, batch.batch,
                                               batch.edge_attr.squeeze(-1)), batch.y))
            if vl < best - 1e-4:
                best, bad = vl, 0
                best_state = {k: v.detach().clone() for k, v in self.net.state_dict().items()}
            else:
                bad += 1
                if bad >= self.patience:
                    break
        if best_state:
            self.net.load_state_dict(best_state)
        return self

    def predict_proba(self, idx, b: Bundle):
        idx = np.asarray(idx)
        mats = self.conn.transform([b.ts[i] for i in idx])
        graphs = self._graphs(idx, b, mats)
        self.net.eval()
        out = []
        with torch.no_grad():
            for batch in DataLoader(graphs, batch_size=32):
                batch = batch.to(self.device)
                logits = self.net(batch.x, batch.edge_index, batch.batch,
                                  batch.edge_attr.squeeze(-1))
                out.append(F.softmax(logits, dim=1)[:, 1].cpu().numpy())
        return np.concatenate(out)

    def graphs_for(self, idx, b: Bundle):
        """Expose graphs for explainability passes."""
        idx = np.asarray(idx)
        return self._graphs(idx, b, self.conn.transform([b.ts[i] for i in idx]))
