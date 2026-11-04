"""INC-3: an offset is committed only after the batch is processed, or a crash loses events."""
import pytest

from nostradamus.log import Consumer
from tests.helpers import B, drain, harness, overdraft, send


def test_a_crash_before_processing_does_not_lose_the_polled_events(tmp_path):
    log, lake, prod, proc = harness(str(tmp_path))
    send(prod, [overdraft("E1", "2025-03-05T10:00:00+00:00"), overdraft("E2", "2025-03-06T10:00:00+00:00")])

    def boom(*a, **k):
        raise RuntimeError("lake unavailable")

    lake.publish = boom
    with pytest.raises(RuntimeError):
        proc.run_batch()
    # restart: a new consumer in the same group must see both events again
    again = Consumer(log, "events", "g").poll()
    assert sorted(r.value["event_id"] for r in again) == ["E1", "E2"]
