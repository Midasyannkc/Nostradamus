"""INC-1: a log delivers at least once, so the same event can arrive twice. It must count once."""
from tests.helpers import B, drain, harness, overdraft, send


def test_a_redelivered_overdraft_counts_once(tmp_path):
    _, lake, prod, proc = harness(str(tmp_path))
    e = overdraft("E1", "2025-03-05T10:00:00+00:00")
    send(prod, [e, e, overdraft("E2", "2025-03-09T10:00:00+00:00")])
    drain(proc)
    count, amount = proc.state.b[B]["od"][2]
    assert count == 2
    assert lake.count("bronze.events") == 2
