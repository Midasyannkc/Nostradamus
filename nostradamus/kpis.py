"""Outcome KPIs from alerts and the notices of sale the pipeline itself ingested."""
from datetime import datetime, timedelta, timezone

import numpy as np

from .config import HORIZON_DAYS, MONTHS
from .simulate import month_start


def _dt(d):
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def evaluate(alerts: list[dict], state, live_from_month: int, active_borrowers_by_month: dict | None = None) -> dict:
    data_end = _dt(month_start(MONTHS))
    live_start = _dt(month_start(live_from_month))
    nos = {b: datetime.fromisoformat(st["nos"]) for b, st in state.b.items() if st["nos"]}
    live_nos = {b: t for b, t in nos.items() if live_start <= t < data_end}
    first = {}
    for a in sorted(alerts, key=lambda x: x["alert_time"]):
        first.setdefault(a["borrower_id"], a["alert_time"])
    caught = {b: (t - first[b]).total_seconds() / 86400 for b, t in live_nos.items() if b in first and first[b] < t}
    mature = [(b, t) for b, t in first.items() if t + timedelta(days=HORIZON_DAYS) <= data_end]
    hits = [b for b, t in mature if b in nos and t < nos[b] <= t + timedelta(days=HORIZON_DAYS)]
    lead = sorted(caught.values())
    return {
        "live_notices_of_sale": len(live_nos),
        "caught_before_notice": len(caught),
        "recall": round(len(caught) / len(live_nos), 4) if live_nos else None,
        "alerted_borrowers": len(first),
        "alerts": len(alerts),
        "mature_alerted_borrowers": len(mature),
        "hits_within_horizon": len(hits),
        "precision": round(len(hits) / len(mature), 4) if mature else None,
        "median_lead_days": round(float(np.median(lead)), 1) if lead else None,
        "p25_lead_days": round(float(np.percentile(lead, 25)), 1) if lead else None,
        "lead_days_30_plus": sum(1 for x in lead if x >= 30),
    }


def _first_alert(rows):
    first = {}
    for b, t in sorted(rows, key=lambda x: x[1]):
        first.setdefault(b, t)
    return first


def operating_point(scored, state, live_from_month, threshold=None, baseline_dpd=None) -> dict:
    """KPIs for the first alert per borrower under a score threshold, or under the days-past-due rule."""
    if baseline_dpd is not None:
        rows = [(b, t) for b, m, sc, dpd, t in scored if dpd >= baseline_dpd]
    else:
        rows = [(b, t) for b, m, sc, dpd, t in scored if sc >= threshold]
    alerts = [{"borrower_id": b, "alert_time": t} for b, t in rows]
    out = evaluate(alerts, state, live_from_month)
    out["first_alert"] = _first_alert(rows)
    return out


def matched_workload(scored, state, live_from_month, target_borrowers: int) -> tuple[float, dict]:
    """Lowest threshold whose number of distinct alerted borrowers does not exceed the target."""
    lo, hi = 0.0, 1.0
    for _ in range(30):
        mid = (lo + hi) / 2
        n = len({b for b, m, sc, dpd, t in scored if sc >= mid})
        if n > target_borrowers:
            lo = mid
        else:
            hi = mid
    thr = hi
    return thr, operating_point(scored, state, live_from_month, threshold=thr)


def earlier_than_rule(model_first: dict, rule_first: dict, state, live_from_month) -> dict:
    """For borrowers who reached a notice of sale in the live window and were flagged by both, how much earlier did the
    model flag them than the days-past-due rule did."""
    data_end = _dt(month_start(MONTHS))
    live_start = _dt(month_start(live_from_month))
    gaps = []
    only_model = 0
    for b, st in state.b.items():
        if not st["nos"]:
            continue
        nos = datetime.fromisoformat(st["nos"])
        if not (live_start <= nos < data_end):
            continue
        m = model_first.get(b)
        r = rule_first.get(b)
        if m is not None and m < nos and (r is None or r >= nos):
            only_model += 1
        elif m is not None and r is not None and m < nos and r < nos:
            gaps.append((r - m).total_seconds() / 86400)
    gaps.sort()
    return {"both_flagged": len(gaps), "model_earlier": sum(1 for g in gaps if g > 0),
            "median_days_earlier": round(float(np.median(gaps)), 1) if gaps else None,
            "model_only_catches": only_model}
