"""Early-warning model: gradient boosted trees on point-of-month borrower features, plus simple reason codes."""
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from .config import HORIZON_DAYS
from .state import FEATURES, features, month_of

RISK_UP = ["dpd_now", "max_dpd_3m", "late_months_6m", "overdrafts_30d", "overdrafts_90d", "overdraft_amt_90d",
           "utilization_now", "util_delta_3m", "accounts_closed_12m", "new_accounts_90d", "inquiries_90d",
           "other_late_90d", "overspend_index", "household_loans", "household_monthly_debt", "liens_judgments", "ltv",
           "dti"]
RISK_DOWN = ["score_now", "score_delta_3m"]


def month_end_ts(M: int):
    from datetime import datetime, timezone
    from .simulate import month_start
    d = month_start(M + 1)
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def build_training(state, statics: dict, months: range):
    X, y, meta = [], [], []
    for b, st in state.b.items():
        if b not in statics:
            continue
        nos = None if st["nos"] is None else __import__("datetime").datetime.fromisoformat(st["nos"])
        for M in months:
            end = month_end_ts(M)
            if nos is not None and nos <= end:
                continue
            if M not in st["pay"]:
                continue
            X.append(features(st, M, statics[b]))
            hit = nos is not None and end < nos <= end + __import__("datetime").timedelta(days=HORIZON_DAYS)
            y.append(1 if hit else 0)
            meta.append((b, M))
    return np.array(X, float), np.array(y), meta


class Model:
    version = "hgb-1"

    def __init__(self):
        self.clf = HistGradientBoostingClassifier(max_depth=3, learning_rate=.08, max_iter=150, l2_regularization=1.0,
                                                  class_weight="balanced", random_state=0)
        self.threshold = .5

    def fit(self, X, y):
        self.clf.fit(X, y)
        self.median = np.median(X, axis=0)
        self.scale = np.maximum(X.std(axis=0), 1e-9)
        return self

    def predict(self, X):
        return self.clf.predict_proba(X)[:, 1]

    def reasons(self, x, k=3):
        z = (np.asarray(x) - self.median) / self.scale
        sign = np.array([1 if f in RISK_UP else -1 if f in RISK_DOWN else 0 for f in FEATURES])
        order = np.argsort(-(z * sign))[:k]
        return [FEATURES[i] for i in order if z[i] * sign[i] > 0]
