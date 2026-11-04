"""Synthetic mortgage borrowers and their event streams. No real person, bank, bureau or vendor data.

A latent stress process drives, in this order of sensitivity: overdrafts and credit signals first, other-tradeline
lates next, mortgage delinquency last. Once a borrower is 90 or more days behind, the servicer may issue a notice of
default; a notice of sale follows no sooner than the statutory cure period and the sale falls on the first Tuesday that
is at least 21 days after the notice of sale (Texas Property Code 51.002)."""
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd

from . import refdata
from .config import MONTHS, START

BASE_OFFSET = -0.3  # shifts overall stress so the synthetic book has enough foreclosures to measure
SHOCK_P = .02        # monthly chance of a large financial shock (job loss, medical bill)
CURE_DAYS = 20
NOTICE_DAYS = 21


def first_tuesday_on_or_after(d: date) -> date:
    """First Tuesday of a month on or after d (sales happen on the first Tuesday of the month)."""
    y, m = d.year, d.month
    for _ in range(3):
        first = date(y, m, 1)
        tue = first + timedelta(days=(1 - first.weekday()) % 7)
        if tue >= d:
            return tue
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    raise AssertionError("unreachable")


def _sig(x):
    return 1 / (1 + np.exp(-x))


def month_start(i: int) -> date:
    y, m = int(START[:4]), int(START[5:])
    m0 = (m - 1) + i
    return date(y + m0 // 12, m0 % 12 + 1, 1)


def simulate(seed: int = 11, n: int = 10000, months: int = MONTHS, drift_from_month: int | None = 14,
             drift_share: float = 0.08, dup_rate: float = 0.02, late_rate: float = 0.03, junk_rate: float = 0.001):
    rng = np.random.default_rng(seed)
    zips = refdata.zip_areas()
    w = np.where(zips.focus == "plano", 2.2, np.where(zips.focus == "frisco", 2.2, 1.0))
    zi = rng.choice(len(zips), n, p=w / w.sum())
    z = zips.iloc[zi].reset_index(drop=True)
    bid = np.array([f"B{i:06d}" for i in range(1, n + 1)])
    score0 = np.clip(rng.normal(715, 55, n), 560, 830)
    dti = np.clip(rng.normal(.36, .07, n), .15, .6)
    ltv = np.clip(rng.normal(.78, .12, n), .4, .97)
    hh0 = rng.poisson(1.4, n)
    tier = np.where(z.focus.isin(["plano", "frisco"]), 1.35, 1.0)
    balance = np.round(rng.lognormal(12.45, .35, n) * tier, -2)
    base = -(score0 - 690) / 70 * .6 + (dti - .36) * 4 + (ltv - .78) * 2 + .12 * hh0 + BASE_OFFSET
    borrowers = pd.DataFrame({"borrower_id": bid, "zip": z.zip, "city": z.city, "focus": z.focus, "score0": score0.round(),
                              "dti": dti.round(3), "ltv": ltv.round(3), "household_loans0": hh0, "balance": balance})

    s = np.zeros(n)
    late_m = np.zeros(n, int)
    status = np.zeros(n, int)      # 0 current, 1 notice of default, 2 notice of sale, 3 sold, 4 cured in cure period
    nod_ts = {}; nos_ts = {}; sale_ts = {}
    closed_hist = np.zeros((months, n), int)
    hh = hh0.astype(int).copy()
    liens = np.zeros(n, int)
    events = []
    eid = [0]

    def ev(kind, i, when, payload, source):
        eid[0] += 1
        events.append({"event_id": f"E{eid[0]:09d}", "event_type": kind, "schema_version": 1,
                       "event_time": when.isoformat(), "borrower_id": bid[i], "source": source, "payload": payload})

    def at(m_start, day, rng_):
        return datetime(m_start.year, m_start.month, 1, tzinfo=timezone.utc) + timedelta(
            days=int(day) - 1, seconds=int(rng_.integers(0, 86000)))

    for t in range(months):
        ms = month_start(t)
        s = .75 * s + rng.normal(0, .35, n)
        shock = rng.random(n) < SHOCK_P
        s = s + shock * rng.normal(2.2, .6, n)
        d = base + s
        active = status < 3
        miss = (rng.random(n) < _sig(1.6 * d - 3.6)) & active & (status != 2)
        late_prev = late_m.copy()
        catch = (~miss) & (late_m > 0) & (rng.random(n) < .6)
        late_m = np.where(miss, late_m + 1, np.where(catch, late_m - 1, late_m))
        # servicing chain
        start_nod = (late_m >= 3) & (status == 0) & (rng.random(n) < .6)
        for i in np.where(start_nod)[0]:
            day = int(rng.integers(1, 28))
            nod = at(ms, day, rng)
            nod_d = nod.date()
            if rng.random() < .22:
                status[i] = 4
                late_m[i] = 0
                s[i] *= .5
                ev("servicing_status", i, nod + timedelta(days=int(rng.integers(5, 19))), {"status": "CURE"}, "servicer")
                ev("servicing_status", i, nod, {"status": "NOD"}, "servicer")
                continue
            nos_d = nod_d + timedelta(days=CURE_DAYS + 1 + int(rng.integers(0, 10)))  # a full cure period at timestamp level
            sale_d = first_tuesday_on_or_after(nos_d + timedelta(days=NOTICE_DAYS + 1))
            status[i] = 1
            nod_ts[bid[i]] = nod
            nos_ts[bid[i]] = datetime(nos_d.year, nos_d.month, nos_d.day, 12, tzinfo=timezone.utc)
            sale_ts[bid[i]] = datetime(sale_d.year, sale_d.month, sale_d.day, 11, tzinfo=timezone.utc)
            ev("servicing_status", i, nod, {"status": "NOD"}, "servicer")
        end = datetime(month_start(t + 1).year, month_start(t + 1).month, 1, tzinfo=timezone.utc) if t + 1 < months else \
            datetime(month_start(t).year + (month_start(t).month == 12), month_start(t).month % 12 + 1, 1, tzinfo=timezone.utc)
        for b, nos in list(nos_ts.items()):
            i = int(b[1:]) - 1
            if status[i] == 1 and nos < end:
                ev("servicing_status", i, nos, {"status": "NOS"}, "servicer")
                status[i] = 2
            sale = sale_ts.get(b)
            if status[i] == 2 and sale is not None and sale < end:
                ev("servicing_status", i, sale, {"status": "SALE"}, "servicer")
                status[i] = 3

        live = status < 2
        # payments
        for i in np.where(status < 3)[0]:
            if status[i] == 2:
                continue
            missed = bool(miss[i])
            ev("payment", i, at(ms, rng.integers(1, 29), rng),
               {"due_date": ms.isoformat(), "amount_due": round(float(balance[i]) * .0068, 2),
                "amount_paid": 0.0 if missed else round(float(balance[i]) * .0068, 2),
                "days_past_due": int(late_m[i] * 30)}, "servicer")
        # overdrafts
        od = rng.poisson(np.exp(-2.4 + .95 * d)) * live
        for i in np.where(od > 0)[0]:
            for _ in range(int(od[i])):
                ev("overdraft", i, at(ms, rng.integers(1, 29), rng),
                   {"account_id": f"A{i:06d}", "amount": round(float(rng.uniform(20, 400)), 2),
                    "balance_after": round(float(-rng.uniform(5, 300)), 2), "fee": 35.0}, "bank")
        # credit snapshot
        closures = rng.poisson(np.exp(-3.4 + .55 * d)) * live
        closed_hist[t] = closures
        closed12 = closed_hist[max(0, t - 11):t + 1].sum(axis=0)
        newacc = rng.poisson(np.exp(-1.8 + .35 * d)) * live
        hh = hh + rng.poisson(np.exp(-3.4 + .35 * d)) * live
        score = np.clip(score0 - 14 * np.maximum(d, 0) + rng.normal(0, 6, n), 300, 850)
        util = np.clip(.28 + .16 * d + rng.normal(0, .05, n), 0, 1.3)
        oth = rng.poisson(np.exp(-3.3 + .9 * d)) * live
        inq = rng.poisson(np.exp(-.6 + .3 * d)) * live
        for i in np.where(status < 3)[0]:
            ev("credit_snapshot", i, at(ms, rng.integers(2, 28), rng),
               {"score": int(score[i]), "utilization": round(float(util[i]), 3), "accounts_closed_12m": int(closed12[i]),
                "new_accounts_90d": int(newacc[i]), "inquiries_90d": int(inq[i]), "other_tradeline_late_30d": int(oth[i])},
               "bureau")
        # alternative data, quarterly
        if t % 3 == 0:
            liens = liens + rng.poisson(np.exp(-3.6 + .6 * d)) * live
            over = np.clip(48 + 11 * d + rng.normal(0, 6, n), 0, 100)
            for i in np.where(status < 3)[0]:
                ev("alt_signal", i, at(ms, rng.integers(3, 27), rng),
                   {"overspend_index": round(float(over[i]), 1), "household_loan_count": int(hh[i]),
                    "household_monthly_debt": round(float(hh[i] * 430 + rng.normal(0, 80)), 2),
                    "lien_judgment_count": int(liens[i]), "address_changes_12m": int(rng.poisson(.15))}, "altdata")

    # operational noise: arrival time, lateness, duplicates, drift, junk
    rows = []
    for e in events:
        t0 = datetime.fromisoformat(e["event_time"])
        r = rng.random()
        delay = timedelta(hours=float(rng.uniform(0, 6)))
        if r < late_rate:
            delay = timedelta(days=float(rng.uniform(5, 40)))
        e2 = e
        if drift_from_month is not None and e["event_type"] == "payment" and \
                t0 >= datetime(month_start(drift_from_month).year, month_start(drift_from_month).month, 1, tzinfo=timezone.utc) \
                and rng.random() < drift_share:
            p = dict(e["payload"])
            p["dpd"] = p.pop("days_past_due")      # upstream renamed the field and did not bump the version
            e2 = {**e, "payload": p}
        if rng.random() < junk_rate:
            e2 = {**e2, "borrower_id": None} if rng.random() < .5 else {k: v for k, v in e2.items() if k != "event_time"}
        rows.append((t0 + delay, e2))
        if rng.random() < dup_rate:
            rows.append((t0 + delay + timedelta(hours=float(rng.uniform(1, 70))), e2))
    rows.sort(key=lambda x: x[0])
    stream = [(a, e) for a, e in rows]

    truth = pd.DataFrame({"borrower_id": bid})
    truth["nod_ts"] = truth.borrower_id.map(nod_ts)
    truth["nos_ts"] = truth.borrower_id.map(nos_ts)
    truth["sale_ts"] = truth.borrower_id.map(sale_ts)
    return borrowers, stream, truth
