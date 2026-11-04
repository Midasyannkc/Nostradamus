"""Per-borrower state and features. State is keyed by event month so a window can be recomputed when events arrive."""
from collections import defaultdict
from datetime import datetime

from .config import START

Y0, M0 = int(START[:4]), int(START[5:]) - 1


def month_of(ts: str) -> int:
    d = datetime.fromisoformat(ts)
    return (d.year - Y0) * 12 + d.month - 1 - M0


class State:
    def __init__(self):
        self.b = defaultdict(lambda: {"pay": {}, "od": {}, "cr": {}, "alt": {}, "nos": None, "nod": None, "sale": None,
                                      "last": -1, "t": {}})

    def apply(self, e: dict):
        st = self.b[e["borrower_id"]]
        m = month_of(e["event_time"])
        p = e["payload"]
        k = e["event_type"]
        st["last"] = max(st["last"], m)
        if k in ("payment", "credit_snapshot", "alt_signal"):
            # the newest event by event time wins, whatever order the events arrive in
            if e["event_time"] < st["t"].get((k, m), ""):
                return
            st["t"][(k, m)] = e["event_time"]
        if k == "payment":
            st["pay"][m] = (p.get("days_past_due", 0), 1 if p.get("amount_paid", 0) == 0 else 0)
        elif k == "overdraft":
            c, a = st["od"].get(m, (0, 0.0))
            st["od"][m] = (c + 1, a + p.get("amount", 0.0))
        elif k == "credit_snapshot":
            st["cr"][m] = (p.get("score", 0), p.get("utilization", 0), p.get("accounts_closed_12m", 0),
                           p.get("new_accounts_90d", 0), p.get("inquiries_90d", 0), p.get("other_tradeline_late_30d", 0))
        elif k == "alt_signal":
            st["alt"][m] = (p.get("overspend_index", 0), p.get("household_loan_count", 0),
                            p.get("household_monthly_debt", 0), p.get("lien_judgment_count", 0))
        elif k == "servicing_status":
            s = p.get("status")
            if s == "NOD":
                st["nod"] = e["event_time"]
            elif s == "NOS":
                st["nos"] = e["event_time"]
            elif s == "SALE":
                st["sale"] = e["event_time"]


FEATURES = ["dpd_now", "max_dpd_3m", "late_months_6m", "overdrafts_30d", "overdrafts_90d", "overdraft_amt_90d",
            "score_now", "score_delta_3m", "utilization_now", "util_delta_3m", "accounts_closed_12m", "new_accounts_90d",
            "inquiries_90d", "other_late_90d", "overspend_index", "household_loans", "household_monthly_debt",
            "liens_judgments", "ltv", "dti"]


def _latest(d: dict, M: int):
    ks = [k for k in d if k <= M]            # only what was known by the end of month M
    return d[max(ks)] if ks else None


def features(st: dict, M: int, static: dict) -> list:
    pay, od, cr, alt = st["pay"], st["od"], st["cr"], st["alt"]
    p = _latest(pay, M) or (0, 0)
    c = _latest(cr, M) or (0, 0, 0, 0, 0, 0)
    c3 = cr.get(M - 3) or c
    a = _latest(alt, M) or (0, 0, 0, 0)
    dpds = [pay[m][0] for m in range(M - 2, M + 1) if m in pay]
    late6 = sum(1 for m in range(M - 5, M + 1) if m in pay and pay[m][0] > 0)
    od90 = [od.get(m, (0, 0.0)) for m in range(M - 2, M + 1)]
    oth = sum(cr[m][5] for m in range(M - 2, M + 1) if m in cr)
    return [p[0], max(dpds) if dpds else 0, late6, od.get(M, (0, 0.0))[0], sum(x[0] for x in od90), sum(x[1] for x in od90),
            c[0], c[0] - c3[0], c[1], c[1] - c3[1], c[2], c[3], c[4], oth, a[0], a[1], a[2], a[3],
            static["ltv"], static["dti"]]
