select event_id, borrower_id, event_time,
       json_extract(payload, '$.days_past_due')::int as days_past_due,
       json_extract(payload, '$.amount_paid')::double as amount_paid
from {{ source('bronze', 'events') }}
where event_type = 'payment'
