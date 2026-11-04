-- Snowflake design for the near-real-time layer. In this repo the same logic runs as dbt models on DuckDB.
-- Dynamic Tables keep these results fresh within the target lag without a hand-written schedule.

create or replace dynamic table NOSTRADAMUS.SILVER.STG_OVERDRAFTS
  target_lag = '5 minutes' warehouse = NOSTRADAMUS_WH
as
select event_id, borrower_id, event_time,
       datediff('month', '2025-01-01'::timestamp_ntz, convert_timezone('UTC', event_time)::timestamp_ntz) as month_idx,
       payload:amount::float as amount
from NOSTRADAMUS.BRONZE.EVENTS
where event_type = 'overdraft';

create or replace dynamic table NOSTRADAMUS.GOLD.FCT_ALERT_OUTCOMES
  target_lag = '15 minutes' warehouse = NOSTRADAMUS_WH
as
select a.borrower_id, min(a.alert_time) as first_alert_time, count(*) as alerts
from NOSTRADAMUS.SILVER.STG_ALERTS a
group by a.borrower_id;

-- Unstructured data: servicer letters land in a stage, Cortex extracts a hardship flag for analyst review.
-- create or replace stage NOSTRADAMUS.BRONZE.SERVICER_LETTERS directory = (enable = true);
