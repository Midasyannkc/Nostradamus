"""Stream processor: consume the log, update borrower state, publish to the lake, close months, score, alert."""
import json
import uuid
from datetime import datetime, timedelta

import numpy as np

from . import contracts
from .config import ALLOWED_LATENESS_DAYS, COOLDOWN_DAYS
from .lake import AuditFailed
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
        self.seen = {}
        self.stats = {"batches": 0, "events": 0, "published": 0, "duplicates": 0, "dead_letter": {}, "batch_ms": []}
        self.alarms = set()
        self.last_alert = {}

    def run_batch(self) -> int:
        recs = self.consumer.poll()
        if not recs:
            return 0
        import time
        t0 = time.perf_counter()
        good, dlq = [], []
        for r in recs:
            e = r.value
            reason = contracts.validate(e)
            if reason:
                dlq.append({"raw": json.dumps(e, default=str), "reason": reason})
                self._count_dead(reason)
                continue
            if e["event_id"] in self.seen:               # at-least-once delivery: count each event once
                self.stats["duplicates"] += 1
                continue
            ts = datetime.fromisoformat(e["event_time"])
            if self.max_t is None or ts > self.max_t:
                self.max_t = ts
            if ts < self.max_t - timedelta(days=ALLOWED_LATENESS_DAYS):
                dlq.append({"raw": json.dumps(e, default=str), "reason": "late_beyond_allowed"})
                self._count_dead("late_beyond_allowed")
                continue
            self.seen[e["event_id"]] = ts
            good.append(e)
        batch_id = uuid.uuid4().hex[:12]
        try:
            self.lake.publish(batch_id, good)
        except AuditFailed as err:
            # keep the data, but out of bronze: park the whole batch in the dead-letter table and raise an alarm
            dlq += [{"raw": json.dumps(e, default=str), "reason": "audit_failed"} for e in good]
            self._count_dead("audit_failed", len(good))
            self.alarms.add("audit_failed")
            good = []
        for e in good:                                   # state follows the lake: only published events are applied
            self.state.apply(e)
        if dlq:
            from .lake import now
            ing = now()
            self.lake.append("bronze.dead_letter", [{**d, "batch_id": batch_id, "ingested_at": ing} for d in dlq])
            if len(recs) >= 50 and len(dlq) / len(recs) >= .02:
                self.alarms.add("contract_drift")
        self.stats["published"] += len(good)
        self.stats["events"] += len(recs)
        self.stats["batches"] += 1
        self._close_months()
        self.consumer.commit()
        self.stats["batch_ms"].append((time.perf_counter() - t0) * 1000)
        return len(recs)

    def _count_dead(self, reason, n=1):
        self.stats["dead_letter"][reason] = self.stats["dead_letter"].get(reason, 0) + n

    def _prune_seen(self):
        cutoff = self.max_t - timedelta(days=ALLOWED_LATENESS_DAYS + 5)
        if len(self.seen) > 400_000:
            self.seen = {k: v for k, v in self.seen.items() if v >= cutoff}

    def _close_months(self):
        self._prune_seen()
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
            prev = self.last_alert.get(b)
            quiet = prev is not None and (when - prev[0]).days < COOLDOWN_DAYS and X[i][0] < prev[1] + 30
            if score[i] >= self.model.threshold and not quiet:
                self.last_alert[b] = (when, X[i][0])
                a = {"alert_id": uuid.uuid4().hex[:12], "borrower_id": b, "as_of_month": M, "alert_time": when,
                     "score": float(score[i]), "reasons": self.model.reasons(X[i]), "model_version": self.model.version}
                self.alerts.append(a)
                if self.alerts_out:
                    self.alerts_out.append("alerts", b, {**a, "alert_time": a["alert_time"].isoformat()})
