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


def run(out: str, seed: int = 11, n: int = 10000, concurrent: bool = True, drift: bool = True) -> dict:
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    borrowers, stream, truth = simulate.simulate(seed=seed, n=n, drift_from_month=16 if drift else None)
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
    X, y, meta = M.build_training(state, statics, range(0, TRAIN_MONTHS))   # only rows with a closed label window
    Xv, _, _ = M.build_training(state, statics, range(TRAIN_MONTHS - 1, TRAIN_MONTHS), labeled_only=False)
    model = M.Model().fit(X, y)
    model.threshold = float(np.quantile(model.predict(Xv), .985))   # label free: top 1.5 percent of the latest month
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
    replayed = proc.replay_dead_letter() if drift else 0
    lake.append("gold.alerts", [{**a, "reasons": json.dumps(a["reasons"])} for a in proc.alerts])
    k = kpis.evaluate(proc.alerts, state, TRAIN_MONTHS)
    kb = kpis.evaluate(proc.baseline, state, TRAIN_MONTHS)
    rule = kpis.operating_point(proc.scored, state, TRAIN_MONTHS, baseline_dpd=60)
    thr_eq, matched = kpis.matched_workload(proc.scored, state, TRAIN_MONTHS, rule["alerted_borrowers"])
    earlier = kpis.earlier_than_rule(matched.pop("first_alert"), rule.pop("first_alert"), state, TRAIN_MONTHS)
    ms = np.array(proc.stats["batch_ms"])
    report = {"events_streamed": len(stream), "borrowers": n, "model": k, "baseline_dpd60": kb, "equal_workload": {"model": matched, "rule_dpd60": rule,
              "threshold": round(thr_eq, 4), "earlier": earlier}, "dead_letter": proc.stats["dead_letter"],
              "duplicates_removed": proc.stats["duplicates"], "replayed_from_dead_letter": replayed,
              "bronze_events": lake.count("bronze.events"), "alarms": sorted(proc.alarms),
              "stream": {"events": proc.stats["events"], "published": proc.stats["published"], "batches": proc.stats["batches"],
                         "p50_batch_ms": round(float(np.percentile(ms, 50)), 1), "p95_batch_ms": round(float(np.percentile(ms, 95)), 1)},
              "train_rows": int(len(y)), "train_positives": int(y.sum())}
    import pandas as pd
    borrowers.to_parquet(os.path.join(out, "borrowers.parquet"))
    od = [(b, m, c, a) for b, st in state.b.items() if b in statics for m, (c, a) in st["od"].items()]
    pd.DataFrame(od, columns=["borrower_id", "month_idx", "overdrafts", "overdraft_amount"]).to_parquet(os.path.join(out, "python_overdrafts.parquet"))
    json.dump(report, open(os.path.join(out, "report.json"), "w"), indent=1, default=str)
    return report


def run_all(base: str) -> dict:
    """The headline run with upstream schema drift, and a reference run without it to price the drift."""
    main = run(os.path.join(base, "run"), drift=True)
    ref = run(os.path.join(base, "run_no_drift"), drift=False)
    main["no_drift_reference"] = {"model": ref["model"], "equal_workload": ref["equal_workload"]}
    json.dump(main, open(os.path.join(base, "report.json"), "w"), indent=1, default=str)
    return main


if __name__ == "__main__":
    print(json.dumps(run_all(os.path.join(ROOT, "out")), indent=1, default=str))
