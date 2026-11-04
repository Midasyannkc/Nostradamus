"""INC-8: a borrower who stays above the threshold is alerted once per cooldown, unless things get worse."""
import numpy as np

from nostradamus.state import FEATURES
from tests.helpers import B, drain, harness, pay, send


class AlwaysHigh:
    version = "stub"
    threshold = .5

    def predict(self, X):
        return np.full(len(X), .9)

    def reasons(self, x, k=3):
        return ["dpd_now"]


def _run(tmp_path, dpds):
    _, _, prod, proc = harness(str(tmp_path), model=AlwaysHigh())
    events = [pay(f"E{i}", f"2025-{i + 1:02d}-10T10:00:00+00:00", dpd=d) for i, d in enumerate(dpds)]
    events.append(pay("Z", "2025-%02d-20T10:00:00+00:00" % (len(dpds) + 2)))   # advances the watermark past the last month
    send(prod, events)
    drain(proc)
    return proc


def test_a_persistently_high_borrower_is_not_alerted_every_month(tmp_path):
    proc = _run(tmp_path, [0, 0, 0, 0, 0, 0])
    times = [a["alert_time"] for a in proc.alerts if a["borrower_id"] == B]
    assert len(times) >= 1
    assert all((b - a).days >= 60 for a, b in zip(times, times[1:]))


def test_a_borrower_who_gets_worse_is_alerted_again_inside_the_cooldown(tmp_path):
    proc = _run(tmp_path, [0, 0, 60, 90])
    months = sorted(a["as_of_month"] for a in proc.alerts if a["borrower_id"] == B)
    assert months == [0, 2, 3]      # month 1 is suppressed, the jumps to 60 and 90 days past due are not
