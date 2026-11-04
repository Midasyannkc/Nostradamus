# ADR 0004: DuckDB stands in for Snowflake

Status: accepted. No Snowflake account was available. dbt models run on DuckDB and the Snowflake Dynamic Table SQL in `snowflake/` is written but was never executed. The two share the same logic, and the SQL results are reconciled to the Python processor (8 of 8 KPIs, 0 of 22,266 overdraft borrower-months differing).
