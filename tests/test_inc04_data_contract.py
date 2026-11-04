"""INC-4: events that break the contract go to a dead-letter table with a reason. They never become silent zeros."""
from tests.helpers import B, drain, harness, pay, send


def _drifted(eid, t, dpd):
    e = pay(eid, t, dpd=dpd)
    e["payload"]["dpd"] = e["payload"].pop("days_past_due")   # upstream renamed the field without a version bump
    return e


def test_a_renamed_field_and_a_missing_borrower_go_to_the_dead_letter_table(tmp_path):
    _, lake, prod, proc = harness(str(tmp_path))
    send(prod, [_drifted("E1", "2025-03-05T10:00:00+00:00", 90), pay("E2", "2025-03-06T10:00:00+00:00", b=None),
                pay("E3", "2025-04-06T10:00:00+00:00", dpd=30)])
    drain(proc)
    reasons = " ".join(r["reason"] for r in lake.rows("bronze.dead_letter"))
    assert "days_past_due" in reasons and "borrower_id" in reasons
    assert None not in proc.state.b                       # no ghost borrower
    assert 2 not in proc.state.b[B]["pay"]               # the drifted 90 days past due was not stored as 0
    assert lake.count("bronze.events") == 1


def test_a_burst_of_contract_violations_raises_a_drift_alarm(tmp_path):
    _, _, prod, proc = harness(str(tmp_path))
    events = [pay(f"E{i}", "2025-03-%02dT10:00:00+00:00" % (i % 27 + 1)) for i in range(90)]
    events += [_drifted(f"D{i}", "2025-03-%02dT11:00:00+00:00" % (i % 27 + 1), 30) for i in range(10)]
    send(prod, events)
    drain(proc)
    assert "contract_drift" in proc.alarms
