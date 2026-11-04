# Incident log

Every incident has two commits. The first adds a test that fails for the right reason; a later one fixes the code and the same test passes. Hashes below come from `git log`.

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

### INC-1: A redelivered overdraft was counted twice

The log delivers at least once, so a consumer restart redelivers events. State and the lake both counted the second copy. The processor now remembers processed event ids and drops repeats, counting them for the report.

Reproduce `4680b6e`, fix `3fe28c3`. Found by: duplicate test after at-least-once redelivery.

### INC-2: A late older payment overwrote a newer one

Within a month the processor kept whichever payment, credit or alt-data event arrived last. A late older event replaced newer days past due. State now keeps the event with the newest event time.

Reproduce `cd46b24`, fix `70707b0`. Found by: out-of-order replay test.

### INC-3: Offsets were committed before processing, so a crash lost events

The consumer committed its offset on poll. A crash after the poll and before processing skipped those events forever. Offsets are now committed only after the batch is published and applied.

Reproduce `ffbf656`, fix `9c00212`. Found by: crash-between-poll-and-process test.

### INC-4: A renamed field loaded as zero and a null borrower created a ghost borrower

The upstream servicer renamed days_past_due to dpd with no version bump, which loaded as zero days late, and events without a borrower id created a ghost borrower. Every event is validated against a contract, violations go to a dead-letter table, a drift alarm fires, and confirmed aliases can be replayed.

Reproduce `d34edd4`, fix `358a199`. Found by: upstream drift in the simulator.

### INC-5: A retried batch was stored twice

A batch that failed after writing was written again on retry. Each batch is now staged in its own table, audited, then published once, keyed by a batch id stored as a snapshot property.

Reproduce `0c917f7`, fix `b18921d`. Found by: retry test on the Iceberg writer.

### INC-6: Features for an earlier month changed when later months arrived

Training features read the latest state, so the future leaked into the past. Features are now built only from months up to the as-of month.

Reproduce `eaa6ec6`, fix `0638504`. Found by: point-in-time leakage test.

### INC-7: A very late event changed state without reaching the lake

Events beyond the allowed lateness still changed in-memory state, and a failed audit still changed state. They are parked in the dead-letter table and state is applied only after the lake publish.

Reproduce `c26d7ed`, fix `5f9c52e`. Found by: late-event and failed-audit test.

### INC-8: A borrower above the threshold was alerted every month

The same high-risk borrower was re-alerted each month, flooding the outreach queue. Repeat alerts are suppressed for 60 days unless days past due rises by 30 or more.

Reproduce `0396465`, fix `1acf4aa`. Found by: alert volume check.

### INC-9: The model used a ZIP-level area risk feature, a geographic proxy

Area risk by ZIP can act as a proxy for redlining. The feature was removed and a test now fails if any geographic feature returns. Scores use only borrower finances and loan terms.

Reproduce `63c0a95`, fix `f822ead`. Found by: fairness review.

### INC-10: A future-dated event pushed the watermark and every later event was dropped as late

One bad timestamp moved the watermark far ahead, so real events looked late. Events more than 62 days ahead of the watermark are quarantined.

Reproduce `f150c6d`, fix `a9d3a89`. Found by: junk timestamp test.

### INC-11: Training labeled unfinished windows as negatives

Borrower-months whose 180 day window had not closed were counted as non-foreclosures, which biased the model. Training uses matured windows only, and the alert threshold is set without labels from the top 1.5 percent of the latest month.

Reproduce `087b5b3`, fix `b00b14c`. Found by: label maturity check.

### INC-12: SQL months shifted with the session time zone

The dbt overdraft model cast event time in the session time zone, America/Chicago, so events near month boundaries landed in a different month than the processor's UTC buckets. 646 of 22,442 borrower-months disagreed. Months are now bucketed in UTC and the reconciliation shows zero mismatches.

Reproduce `cef33a8`, fix `1312b34`. Found by: warehouse reconciliation against the processor.
