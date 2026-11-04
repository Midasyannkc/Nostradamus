"""INC-12: month bucketing in SQL must not depend on the session time zone. Events are stamped in UTC."""
import os
import re

import duckdb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _month_idx(session_tz: str) -> int:
    sql = open(os.path.join(ROOT, "dbt/models/silver/stg_overdrafts.sql")).read()
    sql = re.sub(r"\{\{\s*source\('bronze',\s*'events'\)\s*\}\}", "bronze.events", sql)
    con = duckdb.connect()
    con.execute(f"set TimeZone='{session_tz}'")
    con.execute("create schema bronze")
    con.execute("create table bronze.events (event_id varchar, event_type varchar, borrower_id varchar, "
                "event_time timestamptz, payload varchar)")
    # 00:30 UTC on 1 March 2025 is still 28 February in Chicago
    con.execute("insert into bronze.events values ('E1', 'overdraft', 'B1', '2025-03-01 00:30:00+00', '{\"amount\": 40.0}')")
    return con.execute(sql).fetchone()[3]


def test_month_index_is_the_same_in_every_session_time_zone():
    assert _month_idx("UTC") == 2
    assert _month_idx("America/Chicago") == 2
