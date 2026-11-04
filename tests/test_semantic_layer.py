"""The MetricFlow definitions must stay in step with the SQL KPI mart."""
import os

import duckdb
import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "out", "nostradamus.duckdb")
SEM = yaml.safe_load(open(os.path.join(ROOT, "dbt/models/semantic.yml")))


def test_core_metrics_are_defined_once():
    names = [m["name"] for m in SEM["metrics"]]
    assert len(names) == len(set(names))
    assert {"alert_precision", "mean_lead_days", "alerted_borrowers"} <= set(names)


def test_precision_is_hits_over_matured_alerts():
    m = next(x for x in SEM["metrics"] if x["name"] == "alert_precision")
    assert m["type"] == "ratio"
    assert m["type_params"] == {"numerator": "hit_borrowers", "denominator": "matured_alerted_borrowers"}


@pytest.mark.skipif(not os.path.exists(DB), reason="warehouse not built")
def test_semantic_measures_equal_the_kpi_mart():
    con = duckdb.connect(DB, read_only=True)
    sem = con.execute("select sum(case when matured and hit then 1 else 0 end), sum(case when matured then 1 else 0 end) "
                      "from gold.fct_alert_outcomes").fetchone()
    mart = dict(con.execute("select metric, value from gold.mart_kpis").fetchall())
    assert sem[0] == mart["hits_within_horizon"] and sem[1] == mart["mature_alerted_borrowers"]
