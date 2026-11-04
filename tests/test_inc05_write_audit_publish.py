"""INC-5: write, audit, publish. A retried batch is a no-op and a batch that fails its audit never reaches bronze."""
import pytest

from nostradamus.lake import Lake
from tests.helpers import overdraft


def _events(n, start=1):
    return [overdraft(f"E{i}", "2025-03-05T10:00:00+00:00") for i in range(start, start + n)]


def test_publishing_the_same_batch_twice_is_idempotent(tmp_path):
    lake = Lake(str(tmp_path))
    lake.publish("b1", _events(3))
    lake.publish("b1", _events(3))            # an orchestrator retry
    assert lake.count("bronze.events") == 3


def test_a_batch_that_fails_its_audit_is_not_published(tmp_path):
    lake = Lake(str(tmp_path))
    lake.publish("b1", _events(3))
    with pytest.raises(ValueError):
        lake.publish("b2", _events(3, start=3))   # E3 is already in bronze
    assert lake.count("bronze.events") == 3
    assert not [t for t in lake.cat.list_tables("stage")]    # nothing left staged
