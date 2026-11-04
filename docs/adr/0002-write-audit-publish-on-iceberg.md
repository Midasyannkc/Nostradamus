# ADR 0002: Write, audit, publish on Iceberg

Status: accepted. Each micro-batch is written to its own staging table, audited (no null keys, no duplicate event ids, row counts), then appended to the published table with a snapshot property `nostra.batch_id`. A retry finds the batch id and does nothing. Consequence: bad data never reaches readers, and a crash mid-batch is safe (incidents 5 and 7).
