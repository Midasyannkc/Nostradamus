# AI development log

Built in one session with Claude as the coding assistant. Christian Kouadio Kouassi is the author and owner of every commit.

## What the assistant generated

The Python source, tests, dbt models, MetricFlow definitions, Airflow DAG, Terraform and Snowflake files, docs and deck.

## What was checked, and how

- Every incident has a failing test first, run in clean worktrees by `scripts/verify_incidents.py` (12 of 12 pass).
- dbt: 29 models and tests pass. The warehouse KPIs equal the Python KPIs on 8 of 8 metrics and the overdraft month table has 0 mismatches in 22,266 rows.
- MetricFlow `validate-configs` passes against the warehouse and its precision matches the SQL mart.
- The Airflow DAG imports, maps over areas, and its publish step was tested for idempotency and for blocking duplicates.

## Wrong first attempts

- The first model showed no lift because the simulated signals moved at the same time as the missed payment. A liquidity buffer, a burn-in period and a 180 day horizon were added so strain shows before the miss. Earlier reports are kept in `docs/`.
- A ghost-borrower error was first patched with guards, then fixed properly by the data contract (incident 4).
- The warehouse disagreed with the processor on 646 borrower-months because of a session time zone (incident 12).

## What was not verified

- Nothing was run on Azure, Snowflake or a Kafka broker. Terraform was not planned or applied.
- No real LexisNexis, bureau, bank or servicer data. All borrower events are synthetic.
- The model does not beat a 60 day past due rule at equal workload on this data.
