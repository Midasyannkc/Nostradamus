"""Load the published Iceberg snapshots and reference files into DuckDB, the stand-in for Snowflake, for dbt."""
import json
import os

import duckdb
import pandas as pd

from . import refdata
from .lake import Lake


def build(run_dir: str, db_path: str, report: dict | None = None) -> dict:
    if os.path.exists(db_path):
        os.remove(db_path)
    lake = Lake(os.path.join(run_dir, "lake"))
    con = duckdb.connect(db_path)
    for sch in ("bronze", "ref", "silver", "gold"):
        con.execute(f"create schema if not exists {sch}")
    for name, tbl in (("bronze.events", "events"), ("bronze.dead_letter", "dead_letter"), ("gold.alerts", "alerts")):
        arrow = lake.table(name).scan().to_arrow()
        con.register("_t", arrow)
        con.execute(f"create or replace table bronze.{tbl} as select * from _t")
        con.unregister("_t")
    con.register("b", pd.read_parquet(os.path.join(run_dir, "borrowers.parquet")))
    con.execute("create table ref.borrowers as select * from b")
    con.register("z", refdata.zip_areas())
    con.execute("create table ref.zip_areas as select * from z")
    con.register("d", refdata.dallas_notice_files())
    con.execute("create table ref.dallas_notice_files as select * from d")
    con.register("a", refdata.attom_texas())
    con.execute("create table ref.attom_texas as select * from a")
    con.register("o", pd.read_parquet(os.path.join(run_dir, "python_overdrafts.parquet")))
    con.execute("create table ref.python_overdrafts as select * from o")
    rep = report or json.load(open(os.path.join(run_dir, "report.json")))
    rows = []
    for k, v in rep["model"].items():
        rows.append((k, float(v) if v is not None else None))
    con.register("k", pd.DataFrame(rows, columns=["metric", "value"]))
    con.execute("create table ref.python_kpis as select * from k")
    n = {t: con.execute(f"select count(*) from {t}").fetchone()[0] for t in ("bronze.events", "bronze.dead_letter", "bronze.alerts")}
    con.close()
    return n


def run_dbt(db_path: str, command: str = "build", root: str | None = None):
    import subprocess
    import sys
    from .config import ROOT
    env = dict(os.environ, NOSTRADAMUS_DB=os.path.abspath(db_path), DBT_SEND_ANONYMOUS_USAGE_STATS="False")
    return subprocess.run([sys.executable, "-m", "dbt.cli.main", command, "--project-dir", "dbt", "--profiles-dir", "dbt"],
                          cwd=root or ROOT, env=env, capture_output=True, text=True)


def reconcile(db_path: str) -> dict:
    """Compare the SQL results with what the stream processor computed independently."""
    con = duckdb.connect(db_path, read_only=True)
    kpi = con.execute("""select s.metric, s.value as sql_value, p.value as python_value
                         from gold.mart_kpis s left join ref.python_kpis p using (metric)""").df()
    kpi["match"] = (kpi.sql_value - kpi.python_value).abs() < 1e-6
    od = con.execute("""select count(*) n,
                               sum(case when s.borrower_id is null or p.borrower_id is null
                                        or s.overdrafts <> p.overdrafts then 1 else 0 end) mismatches
                        from gold.fct_overdraft_month s
                        full outer join ref.python_overdrafts p using (borrower_id, month_idx)""").fetchone()
    con.close()
    return {"kpi_rows": len(kpi), "kpi_mismatches": kpi[~kpi.match].to_dict("records"),
            "overdraft_month_rows": int(od[0]), "overdraft_month_mismatches": int(od[1])}
