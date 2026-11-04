select event_id, borrower_id, event_time, json_extract_string(payload, '$.status') as status
from {{ source('bronze', 'events') }}
where event_type = 'servicing_status'
