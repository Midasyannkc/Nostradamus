"""INC-10: one future-dated event must not move the watermark and make every real event look late."""
from datetime import datetime, timezone

from tests.helpers import B, drain, harness, pay, send


def test_a_future_dated_event_is_quarantined_and_does_not_advance_the_watermark(tmp_path):
    _, lake, prod, proc = harness(str(tmp_path))
    send(prod, [pay("E1", "2025-03-10T10:00:00+00:00"), pay("E2", "2031-03-10T10:00:00+00:00"),
                pay("E3", "2025-04-10T10:00:00+00:00", dpd=30)])
    drain(proc)
    assert proc.max_t < datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert "event_time_in_future" in " ".join(r["reason"] for r in lake.rows("bronze.dead_letter"))
    assert 3 in proc.state.b[B]["pay"]                       # the real April payment is still accepted
