select s.borrower_id
from {{ ref('stg_servicing') }} s
join {{ ref('stg_servicing') }} n on n.borrower_id = s.borrower_id and n.status = 'NOS'
where s.status = 'SALE' and s.event_time < n.event_time + to_days(21)
