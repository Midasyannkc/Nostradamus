"""INC-11: a training row's label is known only after its whole horizon has passed. Open windows are not labeled 0."""
from nostradamus.config import HORIZON_DAYS
from nostradamus.model import build_training, month_end_ts
from nostradamus.state import State
from tests.helpers import B, pay

STATIC = {B: {"ltv": .8, "dti": .35}}


def test_rows_whose_label_window_extends_past_the_data_are_not_trained_on():
    s = State()
    for m in (3, 4, 5):    # payments in April, May and June 2025
        s.apply(pay(f"E{m}", f"2025-{m + 1:02d}-10T10:00:00+00:00", dpd=30))
    latest_month = 5
    X, y, meta = build_training(s, STATIC, range(0, 6))
    data_end = month_end_ts(latest_month)
    for _, M in meta:
        assert (month_end_ts(M) - data_end).days + HORIZON_DAYS <= 0, f"month {M} has an open label window"
    assert len(meta) == 0     # with only three months of data and a 180 day horizon, no row is labeled yet
