select event_id, borrower_id, event_time,
       date_diff('month', timestamp '2025-01-01', (event_time at time zone 'UTC')) as month_idx,
       json_extract(payload, '$.amount')::double as amount
from {{ source('bronze', 'events') }}
where event_type = 'overdraft'
