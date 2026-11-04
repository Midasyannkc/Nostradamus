"""End to end run: simulate, stream history, train, stream the live months concurrently, score, alert, report."""
import json
import os
import shutil
import threading
import time
from datetime import datetime, timezone

import numpy as np

from . import kpis, model as M, refdata, simulate
from .config import MONTHS, ROOT, TRAIN_MONTHS
from .lake import Lake
from .log import Consumer, Log, Producer
from .processor import Processor
from .state import State


def statics_from(borrowers):
    return {r.borrower_id: {"ltv": float(r.ltv), "dti": float(r.dti)} for r in borrowers.itertuples()}


def area_risk(state, borrowers):
    z = dict(zip(borrowers.borrower_id, borrowers.zip))
    hit, tot = {}, {}
    for b, zc in z.items():
        tot[zc] = tot.get(zc, 0) + 1
        if state.b[b]["nos"]:
            hit[zc] = hit.get(zc, 0) + 1
    return {b: hit.get(zc, 0) / tot[zc] for b, zc in z.items()}


def run(out: str, seed: int = 11, n: int = 10000, concurrent: bool = True, drift: bool = True) -> dict:
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    borrowers, stream, truth = simulate.simulate(seed=seed, n=n, drift_from_month=14 if drift else None)
    statics = statics_from(borrowers)
    live_from = datetime(*simulate.month_start(TRAIN_MONTHS).timetuple()[:3], tzinfo=timezone.utc)
    hist = [e for a, e in stream if a < live_from]
    live = [e for a, e in stream if a >= live_from]
    log = Log(os.path.join(out, "log"))
    lake = Lake(os.path.join(out, "lake"))
    prod = Producer(log)
    for e in hist:
        prod.append("events", e.get("borrower_id") or "unknown", e)
    prod.flush()
    state = State()
    proc = Processor(Consumer(log, "events", "nostradamus"), state, statics, lake)
    while proc.run_batch():
        pass
    risk = area_risk(state, borrowers)
    for b in statics:
        statics[b]["area_risk"] = risk[b]
    X, y, meta = M.build_training(state, statics, range(0, TRAIN_MONTHS - 3))
    Xv, yv, _ = M.build_training(state, statics, range(TRAIN_MONTHS - 3, TRAIN_MONTHS))
    model = M.Model().fit(X, y)
    model.threshold = float(np.quantile(model.predict(Xv), .985))
    proc.model = model
    proc.alerts_out = Producer(log)

    done = threading.Event()

    def produce():
        for i in range(0, len(live), 2000):
            for e in live[i:i + 2000]:
                prod.append("events", e.get("borrower_id") or "unknown", e)
            prod.flush()
            time.sleep(.005)
        done.set()

    th = threading.Thread(target=produce) if concurrent else None
    if th:
        th.start()
    else:
        produce()
    t0 = time.perf_counter()
    idle = 0
    while True:
        k = proc.run_batch()
        if k == 0:
            if done.is_set():
                idle += 1
                if idle > 2:
                    break
            time.sleep(.002)
    if th:
        th.join()
    proc.alerts_out.close()
    lake.append("gold.alerts", [{**a, "reasons": json.dumps(a["reasons"])} for a in proc.alerts])
    k = kpis.evaluate(proc.alerts, state, TRAIN_MONTHS)
    kb = kpis.evaluate(proc.baseline, state, TRAIN_MONTHS)
    ms = np.array(proc.stats["batch_ms"])
    report = {"events_streamed": len(stream), "borrowers": n, "model": k, "baseline_dpd60": kb,
              "stream": {"events": proc.stats["events"], "published": proc.stats["published"], "batches": proc.stats["batches"],
                         "p50_batch_ms": round(float(np.percentile(ms, 50)), 1), "p95_batch_ms": round(float(np.percentile(ms, 95)), 1)},
              "train_rows": int(len(y)), "train_positives": int(y.sum())}
    json.dump(report, open(os.path.join(out, "report.json"), "w"), indent=1, default=str)
    return report


if __name__ == "__main__":
    print(json.dumps(run(os.path.join(ROOT, "out", "run")), indent=1, default=str))
