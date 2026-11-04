# Nostradamus

A streaming pipeline that flags Dallas County, Plano and Frisco mortgage borrowers who are likely to reach a foreclosure sale notice within 180 days, so a servicer can offer hardship help early. Built to practice the stack in the DataExpert.io Senior AI Analytics Engineer curriculum: stream processing, Iceberg write-audit-publish, dbt, a MetricFlow semantic layer, Airflow dynamic task mapping, and Snowflake Dynamic Tables as a design.

## Honest scope

* Borrower, loan, bank, credit and alternative-data events are **synthetic**. No LexisNexis, bureau, bank or servicer data is used. See `data/SOURCE.md` for what is real (Texas Property Code 51.002 timing, Dallas County notice file counts, ATTOM Texas figures) and what is not.
* Foreclosure concerns owners and borrowers, so the model works on borrowers, not tenants.
* The model is for outreach, not credit decisions, and uses no geographic features.
* DuckDB stands in for Snowflake. The Terraform and Snowflake SQL were never applied.
* Predictive results prove the pipeline works on a world the author generated. They do not show the signal exists in real servicer data.

## Results (10,000 borrowers, 559,763 events, 10 live months)

| Metric | Value |
| --- | --- |
| Notices of sale in the live window | 201 |
| Flagged before the notice of sale | 184 (91.5%) |
| Median lead time | 51 days |
| Precision, matured 180 day windows | 34.7% (121 of 349) |
| Borrowers alerted | 610 of 10,000 (6.1%) |
| p95 batch time | 564 ms |
| Duplicates removed | 10,880 |
| Contract-drift events replayed from dead letter | 4,565 of 4,668 |

The baseline is a rule of 60 or more days past due. At the same workload (718 borrowers) that rule caught 196 of 201 and the model 191 of 201, with precision 31.8% against 30.9%. **On this synthetic data the model does not beat the rule.** The stream, the data quality controls and the warehouse are the finished work; the model is a working baseline.

## Run

`make test`, `make run`, `make dbt`, `make semantic`. See `docs/architecture.md`.

## Incidents

Twelve problems found while building, each with a failing-test commit then a fix commit. `python3 scripts/verify_incidents.py` checks all of them.

<!-- incidents:start -->
| # | Incident | Found by | Reproduce | Fix |
| --- | --- | --- | --- | --- |
| INC-1 | A redelivered overdraft was counted twice | duplicate test after at-least-once redelivery | `4680b6e` | `3fe28c3` |
| INC-2 | A late older payment overwrote a newer one | out-of-order replay test | `cd46b24` | `70707b0` |
| INC-3 | Offsets were committed before processing, so a crash lost events | crash-between-poll-and-process test | `ffbf656` | `9c00212` |
| INC-4 | A renamed field loaded as zero and a null borrower created a ghost borrower | upstream drift in the simulator | `d34edd4` | `358a199` |
| INC-5 | A retried batch was stored twice | retry test on the Iceberg writer | `0c917f7` | `b18921d` |
| INC-6 | Features for an earlier month changed when later months arrived | point-in-time leakage test | `eaa6ec6` | `0638504` |
| INC-7 | A very late event changed state without reaching the lake | late-event and failed-audit test | `c26d7ed` | `5f9c52e` |
| INC-8 | A borrower above the threshold was alerted every month | alert volume check | `0396465` | `1acf4aa` |
| INC-9 | The model used a ZIP-level area risk feature, a geographic proxy | fairness review | `63c0a95` | `f822ead` |
| INC-10 | A future-dated event pushed the watermark and every later event was dropped as late | junk timestamp test | `f150c6d` | `a9d3a89` |
| INC-11 | Training labeled unfinished windows as negatives | label maturity check | `087b5b3` | `b00b14c` |
| INC-12 | SQL months shifted with the session time zone | warehouse reconciliation against the processor | `cef33a8` | `1312b34` |
<!-- incidents:end -->
