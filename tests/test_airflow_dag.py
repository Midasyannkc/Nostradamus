import os

from airflow.dag_processing.dagbag import DagBag

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _bag():
    return DagBag(os.path.join(ROOT, "airflow/dags"))


def test_dag_imports_without_errors():
    bag = _bag()
    assert not bag.import_errors
    assert "nostradamus_daily" in bag.dags


def test_areas_fan_out_with_dynamic_task_mapping():
    dag = _bag().dags["nostradamus_daily"]
    for tid in ("stage_area", "audit_area", "publish_area"):
        assert dag.get_task(tid).is_mapped


def test_publish_waits_for_audit_and_dbt_waits_for_publish():
    dag = _bag().dags["nostradamus_daily"]
    assert "audit_area" in dag.get_task("publish_area").upstream_task_ids
    assert "publish_area" in dag.get_task("dbt_build").upstream_task_ids
    assert "dbt_build" in dag.get_task("validate_semantic_layer").upstream_task_ids


def test_publish_is_idempotent_and_audit_blocks_duplicates(tmp_path, monkeypatch):
    import duckdb
    import pytest
    db = str(tmp_path / "w.duckdb")
    monkeypatch.setenv("NOSTRADAMUS_DB", db)
    con = duckdb.connect(db)
    con.execute("create schema silver")
    con.execute("create table silver.stg_alerts as select * from (values ('A1','B1'),('A2','B2')) t(alert_id, borrower_id)")
    con.execute("create table silver.dim_borrower as select * from (values ('B1','plano'),('B2','frisco')) t(borrower_id, focus)")
    con.close()
    import importlib.util
    spec = importlib.util.spec_from_file_location("dag_mod", os.path.join(ROOT, "airflow/dags/nostradamus_daily.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    staged = mod.stage_area.function("plano")
    audited = mod.audit_area.function(staged)
    for _ in range(2):
        mod.publish_area.function(audited)
    con = duckdb.connect(db, read_only=True)
    assert con.execute("select count(*) from published.alerts").fetchone()[0] == 1
    con.close()
    con = duckdb.connect(db)
    con.execute("insert into stage.alerts_plano select * from stage.alerts_plano")
    con.close()
    with pytest.raises(ValueError):
        mod.audit_area.function(staged)
