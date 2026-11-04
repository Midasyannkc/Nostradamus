"""Daily Nostradamus orchestration.

The streaming job runs continuously on its own. This DAG handles the batch side around it: it fans out one task per
Dallas County focus area with dynamic task mapping, audits each partition before anything is published (write, audit,
publish), then builds and tests the dbt models and validates the MetricFlow semantic layer.

Every task is idempotent. A retry or a backfill of the same logical date replaces that date's output and never appends.
"""
from datetime import datetime, timedelta

from airflow.sdk import dag, task

import os
import subprocess

import duckdb

AREAS = ["dallas", "plano", "frisco"]


def _db() -> str:
    return os.environ.get("NOSTRADAMUS_DB", "out/nostradamus.duckdb")


@task
def list_areas() -> list[str]:
    return AREAS

@task
def stage_area(area: str) -> dict:
    """Write one area's alerts to a staging table. Dropping and recreating makes a retry safe."""
    con = duckdb.connect(_db())
    con.execute("create schema if not exists stage")
    con.execute("create schema if not exists published")
    tbl = f"stage.alerts_{area}"
    con.execute(f"drop table if exists {tbl}")
    con.execute(f"""create table {tbl} as
                    select a.*, b.focus as area from silver.stg_alerts a
                    join silver.dim_borrower b using (borrower_id) where b.focus = ?""", [area])
    rows = con.execute(f"select count(*) from {tbl}").fetchone()[0]
    con.close()
    return {"area": area, "stage": tbl, "rows": rows}

@task
def audit_area(staged: dict) -> dict:
    """Audit before publish: no null keys and no duplicate alert ids."""
    con = duckdb.connect(_db(), read_only=True)
    t = staged["stage"]
    nulls = con.execute(f"select count(*) from {t} where alert_id is null or borrower_id is null").fetchone()[0]
    dups = con.execute(f"select count(*) - count(distinct alert_id) from {t}").fetchone()[0]
    con.close()
    if nulls or dups:
        raise ValueError(f"audit failed for {t}: {nulls} null keys, {dups} duplicate alert ids")
    return {**staged, "audited": True}

@task
def publish_area(audited: dict) -> str:
    """Publish by replacing the area's partition in one transaction. Running it twice gives the same table."""
    assert audited["audited"], "refusing to publish an unaudited partition"
    con = duckdb.connect(_db())
    con.execute("begin")
    con.execute("create table if not exists published.alerts as select * from " + audited["stage"] + " where false")
    con.execute("delete from published.alerts where area = ?", [audited["area"]])
    con.execute("insert into published.alerts select * from " + audited["stage"])
    con.execute("commit")
    con.close()
    return audited["area"]

@task
def dbt_build(published: list[str]) -> str:
    subprocess.run(["dbt", "build", "--project-dir", "dbt", "--profiles-dir", "dbt"], check=True)
    return "built"

@task
def validate_semantic_layer(_dbt: str) -> str:
    subprocess.run(["mf", "validate-configs"], check=True, cwd="dbt")
    return "valid"


@dag(
    dag_id="nostradamus_daily",
    schedule="0 6 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["foreclosure", "streaming", "dbt", "metricflow"],
)
def nostradamus_daily():
    areas = list_areas()
    staged = stage_area.expand(area=areas)
    audited = audit_area.expand(staged=staged)
    published = publish_area.expand(audited=audited)
    validate_semantic_layer(dbt_build(published))


nostradamus_daily()
