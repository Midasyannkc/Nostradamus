select event_id, borrower_id, event_time,
       json_extract(payload, '$.score')::int as score,
       json_extract(payload, '$.utilization')::double as utilization,
       json_extract(payload, '$.other_tradeline_late_30d')::int as other_tradeline_late_30d
from {{ source('bronze', 'events') }}
where event_type = 'credit_snapshot'
