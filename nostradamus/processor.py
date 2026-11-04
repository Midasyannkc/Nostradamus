"""Stream processor: consume the log, update borrower state, publish to the lake, close months, score, alert."""
import json
import uuid
from datetime import timedelta

import numpy as np

from .config import ALLOWED_LATENESS_DAYS
from .model import month_end_ts
from .state import FEATURES, features, month_of

GRACE_DAYS = 2


class Processor:
    def __init__(self, consumer, state, statics, lake, model=None, alerts_out=None):
        self.consumer, self.state, self.statics, self.lake = consumer, state, statics, lake
        self.model, self.alerts_out = model, alerts_out
        self.max_t = None
        self.next_close = 0
        self.alerts, self.baseline = [], []
        self.stats = {"batches": 0, "events": 0, "published": 0, "batch_ms": []}

    def run_batch(self) -> int:
        recs = self.consumer.poll()
        if not recs:
            return 0
        import time
        t0 = time.perf_counter()
        good = []
        for r in recs:
            e = r.value
            try:
                et = np.datetime64(e["event_time"][:19])
                self.state.apply(e)
            except Exception:
                continue
            ts = __import__("datetime").datetime.fromisoformat(e["event_time"])
            if self.max_t is None or ts > self.max_t:
                self.max_t = ts
            if ts < self.max_t - timedelta(days=ALLOWED_LATENESS_DAYS):
                continue
            good.append(e)
        batch_id = uuid.uuid4().hex[:12]
        self.lake.publish(batch_id, good)
        self.stats["published"] += len(good)
        self.stats["events"] += len(recs)
        self.stats["batches"] += 1
        self._close_months()
        self.stats["batch_ms"].append((time.perf_counter() - t0) * 1000)
        return len(recs)

    def _close_months(self):
        while self.max_t is not None and month_end_ts(self.next_close) + timedelta(days=GRACE_DAYS) <= self.max_t:
            self._close_month(self.next_close)
            self.next_close += 1

    def _close_month(self, M: int):
        if self.model is None:
            return
        keys, X = [], []
        for b, st in self.state.b.items():
            if b not in self.statics or st["nos"] is not None or M not in st["pay"]:
                continue
            keys.append(b)
            X.append(features(st, M, self.statics[b]))
        if not keys:
            return
        X = np.array(X, float)
        score = self.model.predict(X)
        when = month_end_ts(M) + timedelta(days=GRACE_DAYS)
        for i, b in enumerate(keys):
            if X[i][0] >= 60:
                self.baseline.append({"borrower_id": b, "as_of_month": M, "alert_time": when})
            if score[i] >= self.model.threshold:
                a = {"alert_id": uuid.uuid4().hex[:12], "borrower_id": b, "as_of_month": M, "alert_time": when,
                     "score": float(score[i]), "reasons": self.model.reasons(X[i]), "model_version": self.model.version}
                self.alerts.append(a)
                if self.alerts_out:
                    self.alerts_out.append("alerts", b, {**a, "alert_time": a["alert_time"].isoformat()})
