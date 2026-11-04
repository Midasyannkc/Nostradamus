import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(p):
    return open(os.path.join(ROOT, p)).read()


def test_event_hub_partitions_match_the_log():
    from nostradamus.config import PARTITIONS
    assert f"partition_count   = {PARTITIONS}" in _read("terraform/azure/main.tf")


def test_snowflake_buckets_months_in_utc():
    assert "convert_timezone('UTC'" in _read("snowflake/dynamic_tables.sql")


def test_terraform_braces_balance():
    for p in ("terraform/azure/main.tf", "terraform/snowflake/main.tf"):
        t = _read(p)
        assert t.count("{") == t.count("}")


def test_no_secrets_in_infra():
    for p in ("terraform/azure/main.tf", "terraform/snowflake/main.tf", "snowflake/dynamic_tables.sql"):
        assert not re.search(r"(password|secret|token)\s*=", _read(p), re.I)
