"""INC-7: an event older than the allowed lateness is parked and visible, never applied silently."""
from nostradamus.lake import AuditFailed
from tests.helpers import B, drain, harness, pay, send


def test_a_very_late_event_goes_to_the_dead_letter_table_and_not_to_state(tmp_path):
    _, lake, prod, proc = harness(str(tmp_path))
    send(prod, [pay("E1", "2025-06-10T10:00:00+00:00", dpd=30), pay("E2", "2025-01-05T10:00:00+00:00", dpd=90)])
    drain(proc)
    assert "late_beyond_allowed" in " ".join(r["reason"] for r in lake.rows("bronze.dead_letter"))
    assert 0 not in proc.state.b[B]["pay"]
    assert lake.count("bronze.events") == 1


def test_state_only_reflects_events_that_reached_the_lake(tmp_path):
    _, lake, prod, proc = harness(str(tmp_path))

    def refuse(batch_id, events):
        raise AuditFailed("simulated audit failure")

    lake.publish = refuse
    send(prod, [pay("E1", "2025-03-10T10:00:00+00:00", dpd=60)])
    drain(proc)
    assert B not in proc.state.b or not proc.state.b[B]["pay"]
