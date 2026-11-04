"""INC-2: events arrive out of order. An older event that arrives later must not overwrite a newer one."""
from tests.helpers import B, drain, harness, pay, send


def test_an_older_payment_arriving_late_does_not_overwrite_the_newer_one(tmp_path):
    _, _, prod, proc = harness(str(tmp_path))
    send(prod, [pay("E1", "2025-03-20T10:00:00+00:00", dpd=60), pay("E2", "2025-03-10T10:00:00+00:00", dpd=30)])
    drain(proc)
    assert proc.state.b[B]["pay"][2][0] == 60
