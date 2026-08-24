"""Non-deep baselines -- including the two null models that decide whether the
brain result means anything.

At n~66 a linear model on connectivity edges is a genuinely strong competitor to
a graph network, so it is reported as a peer, not as a straw man.  The motion
and behaviour models exist to be *dangerous*: if either matches the brain model,
the brain model is not measuring what the headline claims.
"""
from __future__ import annotations

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from ..graphs import Connectivity, fisher_z, vectorize
from ..validate import Bundle


class ConnEdgeModel:
    """Vectorised connectivity edges -> linear classifier.

    The Connectivity object is fit on training samples only, which matters for
    kind='tangent' (it estimates a group mean covariance).
    """

    def __init__(self, kind: str = "tangent", clf: str = "logreg", C: float = 1.0,
                 z: bool = False, name: str | None = None):
        self.kind, self.clf_name, self.C, self.z = kind, clf, C, z
        self.name = name or f"{kind}+{clf}"

    def _make_clf(self):
        if self.clf_name == "logreg":
            return LogisticRegression(C=self.C, max_iter=5000, class_weight="balanced")
        if self.clf_name == "svm":
            return SVC(C=self.C, kernel="linear", probability=True,
                       class_weight="balanced", random_state=0)
        raise ValueError(self.clf_name)

    def fit(self, idx, b: Bundle):
        ts_tr = [b.ts[i] for i in idx]
        self.conn = Connectivity(kind=self.kind, n_nodes=b.ts[0].shape[1]).fit(ts_tr)
        x = vectorize(self.conn.transform(ts_tr))
        if self.z:
            x = fisher_z(x)
        self.pipe = Pipeline([("sc", StandardScaler()), ("clf", self._make_clf())])
        self.pipe.fit(x, b.y[idx])
        return self

    def predict_proba(self, idx, b: Bundle):
        x = vectorize(self.conn.transform([b.ts[i] for i in idx]))
        if self.z:
            x = fisher_z(x)
        return self.pipe.predict_proba(x)[:, 1]


class TableModel:
    """Classifier over a precomputed per-sample table (motion, behaviour, ...).

    These are the honesty checks.  ``motion`` asks whether head movement alone
    separates the groups; ``behaviour`` asks whether left-hand drawing quality
    does.  Either one scoring highly reframes what the brain model is detecting.
    """

    def __init__(self, table: str, clf: str = "logreg", name: str | None = None):
        self.table, self.clf_name = table, clf
        self.name = name or f"{table}-only"

    def _make_clf(self):
        if self.clf_name == "gb":
            return HistGradientBoostingClassifier(max_iter=200, random_state=0)
        return LogisticRegression(max_iter=5000, class_weight="balanced")

    def fit(self, idx, b: Bundle):
        x = b.tables[self.table][idx]
        self.pipe = Pipeline([("imp", SimpleImputer(strategy="median")),
                              ("sc", StandardScaler()),
                              ("clf", self._make_clf())])
        self.pipe.fit(x, b.y[idx])
        return self

    def predict_proba(self, idx, b: Bundle):
        return self.pipe.predict_proba(b.tables[self.table][idx])[:, 1]


class GraphMetricModel:
    """Gradient boosting on classic graph-theory summaries."""

    def __init__(self, kind: str = "partial correlation", density: float = 0.10,
                 name: str = "graph-metrics+gb"):
        self.kind, self.density, self.name = kind, density, name

    def _feats(self, mats):
        from ..graphs import graph_metrics
        rows = []
        for m in mats:
            g = graph_metrics(m, self.density)
            rows.append(np.concatenate([g["strength"], g["clustering"],
                                        g["betweenness"], g["global_efficiency"]]))
        return np.nan_to_num(np.asarray(rows, dtype=np.float32))

    def fit(self, idx, b: Bundle):
        ts_tr = [b.ts[i] for i in idx]
        self.conn = Connectivity(kind=self.kind, n_nodes=b.ts[0].shape[1]).fit(ts_tr)
        x = self._feats(self.conn.transform(ts_tr))
        self.pipe = Pipeline([("sc", StandardScaler()),
                              ("clf", HistGradientBoostingClassifier(max_iter=200,
                                                                     random_state=0))])
        self.pipe.fit(x, b.y[idx])
        return self

    def predict_proba(self, idx, b: Bundle):
        x = self._feats(self.conn.transform([b.ts[i] for i in idx]))
        return self.pipe.predict_proba(x)[:, 1]
