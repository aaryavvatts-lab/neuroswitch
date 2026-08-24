"""Models for the control analyses.

``DiffConnEdgeModel`` classifies the *within-subject* difference between two
conditions.  Any fixed subject-level property -- head size, vascular anatomy,
baseline motion tendency, scanner day -- appears in both conditions and cancels
in the subtraction, so a signal that survives is task-specific rather than
"these brains look different".

``ResidualizedConnModel`` strips nuisance variables (drawing performance, motion,
age) out of the connectivity features, with the regression fit on training
subjects only.
"""
from __future__ import annotations

import numpy as np
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

from ..graphs import Connectivity, vectorize
from ..validate import Bundle


class DiffConnEdgeModel:
    """Connectivity(condition A) - Connectivity(condition B), then a linear model.

    The paired time series live in ``bundle.node_meta['ts_pair']``.
    """

    def __init__(self, kind: str = "tangent", C: float = 1.0,
                 name: str | None = None):
        self.kind, self.C = kind, C
        self.name = name or f"diff({kind})+logreg"

    def _pair(self, b: Bundle):
        pair = b.node_meta.get("ts_pair")
        if pair is None:
            raise KeyError("DiffConnEdgeModel needs node_meta['ts_pair']")
        return pair

    def _diff(self, idx, b: Bundle):
        pair = self._pair(b)
        a = self.conn.transform([b.ts[i] for i in idx])
        c = self.conn.transform([pair[i] for i in idx])
        return vectorize(a - c)

    def fit(self, idx, b: Bundle):
        pair = self._pair(b)
        # fit the connectivity estimator on training subjects, both conditions
        ts_tr = [b.ts[i] for i in idx] + [pair[i] for i in idx]
        self.conn = Connectivity(kind=self.kind, n_nodes=b.ts[0].shape[1]).fit(ts_tr)
        x = self._diff(idx, b)
        self.pipe = Pipeline([("sc", StandardScaler()),
                              ("clf", LogisticRegression(C=self.C, max_iter=5000,
                                                         class_weight="balanced"))])
        self.pipe.fit(x, b.y[idx])
        return self

    def predict_proba(self, idx, b: Bundle):
        return self.pipe.predict_proba(self._diff(idx, b))[:, 1]


class ResidualizedConnModel:
    """Connectivity edges with nuisance covariates regressed out.

    The covariate model is fit on the training split only; test features are
    residualised with those same coefficients.  Fitting it on everything would
    leak label-correlated variance across the split.
    """

    def __init__(self, covariate_table: str, kind: str = "tangent", C: float = 1.0,
                 name: str | None = None):
        self.covariate_table, self.kind, self.C = covariate_table, kind, C
        self.name = name or f"{kind}-resid({covariate_table})+logreg"

    def _x(self, idx, b: Bundle):
        return vectorize(self.conn.transform([b.ts[i] for i in idx]))

    def fit(self, idx, b: Bundle):
        ts_tr = [b.ts[i] for i in idx]
        self.conn = Connectivity(kind=self.kind, n_nodes=b.ts[0].shape[1]).fit(ts_tr)
        x = self._x(idx, b)
        self.imp = SimpleImputer(strategy="median")
        c = self.imp.fit_transform(b.tables[self.covariate_table][idx])
        self.nuis = LinearRegression().fit(c, x)
        self.pipe = Pipeline([("sc", StandardScaler()),
                              ("clf", LogisticRegression(C=self.C, max_iter=5000,
                                                         class_weight="balanced"))])
        self.pipe.fit(x - self.nuis.predict(c), b.y[idx])
        return self

    def predict_proba(self, idx, b: Bundle):
        x = self._x(idx, b)
        c = self.imp.transform(b.tables[self.covariate_table][idx])
        return self.pipe.predict_proba(x - self.nuis.predict(c))[:, 1]


class CrossConditionWrapper:
    """Fit on one bundle, predict on the matching samples of another.

    Used for train-on-left-hand / test-on-right-hand generalisation.
    """

    def __init__(self, inner, other: Bundle, name: str | None = None):
        self.inner, self.other = inner, other
        self.name = name or f"cross({getattr(inner, 'name', 'model')})"

    def fit(self, idx, b: Bundle):
        self.model = self.inner.fit(idx, b)
        return self

    def predict_proba(self, idx, b: Bundle):
        # map by subject id so the two bundles need not share ordering
        want = b.subs[idx]
        pos = {s: k for k, s in enumerate(self.other.subs)}
        keep = np.array([pos[s] for s in want if s in pos])
        if len(keep) != len(want):
            raise ValueError("cross-condition bundles do not cover the same subjects")
        return self.model.predict_proba(keep, self.other)
