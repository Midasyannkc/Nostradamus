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
