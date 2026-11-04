"""A quarantined event can be replayed once its contract problem is fixed, and only once."""
from nostradamus import contracts
from tests.helpers import B, drain, harness, pay, send


def test_replay_restores_renamed_field_events_after_the_alias_is_confirmed(tmp_path):
    _, lake, prod, proc = harness(str(tmp_path))
    e = pay("E1", "2025-03-05T10:00:00+00:00", dpd=60)
    e["payload"]["dpd"] = e["payload"].pop("days_past_due")
    send(prod, [e, pay("E2", "2025-04-05T10:00:00+00:00")])
    drain(proc)
    assert 2 not in proc.state.b[B]["pay"]
    assert proc.replay_dead_letter() == 1
    assert proc.state.b[B]["pay"][2][0] == 60
    assert proc.replay_dead_letter() == 0           # a second replay finds nothing new
    assert lake.count("bronze.events") == 2
