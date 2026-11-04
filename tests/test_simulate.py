from datetime import timedelta

import pandas as pd

from nostradamus import refdata, simulate


def test_foreclosure_timeline_respects_the_texas_statute():
    rules = refdata.statute()
    _, _, truth = simulate.simulate(seed=3, n=3000)
    t = truth.dropna(subset=["nos_ts"])
    assert len(t) > 10
    assert ((t.nos_ts - t.nod_ts) >= timedelta(days=rules["min_cure_days_after_notice_of_default"])).all()
    sold = t.dropna(subset=["sale_ts"])
    assert ((sold.sale_ts - sold.nos_ts) >= timedelta(days=rules["min_notice_of_sale_days_before_sale"])).all()
    assert (sold.sale_ts.dt.weekday == 1).all() and (sold.sale_ts.dt.day <= 7).all()


def test_first_tuesday_helper():
    from datetime import date
    assert simulate.first_tuesday_on_or_after(date(2026, 3, 3)) == date(2026, 3, 3)
    assert simulate.first_tuesday_on_or_after(date(2026, 3, 4)) == date(2026, 4, 7)


def test_same_seed_same_stream():
    a = simulate.simulate(seed=5, n=300)[1]
    b = simulate.simulate(seed=5, n=300)[1]
    assert [e["event_id"] for _, e in a] == [e["event_id"] for _, e in b]


def test_stream_has_the_operational_noise_the_pipeline_must_handle():
    _, stream, _ = simulate.simulate(seed=5, n=2000, drift_from_month=10, drift_share=.2)
    ids = [e.get("event_id") for _, e in stream]
    assert len(ids) > len(set(ids))                                   # redelivered duplicates
    assert any("dpd" in e["payload"] for _, e in stream if e.get("payload") and e["event_type"] == "payment")  # drift
    assert any(e.get("borrower_id") is None or "event_time" not in e for _, e in stream)      # junk
    times = [pd.Timestamp(e["event_time"]) for _, e in stream if "event_time" in e]
    assert any(b < a for a, b in zip(times, times[1:]))                # out of order


def test_borrowers_are_pseudonymous_and_cover_the_focus_cities():
    b, _, _ = simulate.simulate(seed=5, n=2000)
    assert b.borrower_id.str.match(r"^B\d{6}$").all()
    assert {"Plano", "Frisco"} <= set(b.city)
    assert set(b.columns) == {"borrower_id", "zip", "city", "focus", "score0", "dti", "ltv", "household_loans0", "balance"}
