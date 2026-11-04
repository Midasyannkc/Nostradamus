# Architecture

Flow: simulator (stands in for servicer, bank, credit bureau and alternative-data vendor feeds) to NostraLog (partitioned log) to stream processor (dedup, contract check, event-time state, watermark) to Iceberg lake (write, audit, publish) to model scoring at month close to alerts. A second path loads the published snapshots into the warehouse, where dbt builds silver and gold models and MetricFlow defines the KPIs. Airflow runs the batch side, one mapped task per area.

| Layer | Local build | Production design |
| --- | --- | --- |
| Event stream | NostraLog, 4 partitions | Azure Event Hubs, Kafka API, 4 partitions |
| Lake | Apache Iceberg via pyiceberg, SQLite catalog | Iceberg on ADLS Gen2 |
| Warehouse | DuckDB | Snowflake with Dynamic Tables |
| Transform | dbt, 29 models and tests | same project, Snowflake target |
| Semantic layer | MetricFlow | same |
| Orchestration | Airflow DAG, dynamic task mapping | same |
| Infra | Terraform files, not applied | same |

Event time rules: dedup by event id, lateness window 45 days, forward bound 62 days, month close scoring when the watermark passes month end plus 2 days, alert cooldown 60 days.
