-- Overdrafts per borrower and event month, rebuilt in SQL from the published bronze events. Reconciled to the stream
-- processor's own state.
select borrower_id, month_idx, count(*) as overdrafts, round(sum(amount), 2) as overdraft_amount
from {{ ref('stg_overdrafts') }}
group by 1, 2
