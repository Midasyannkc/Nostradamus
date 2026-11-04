-- Texas Property Code 51.002: a notice of sale cannot precede the end of the cure period after a notice of default.
select n.borrower_id
from {{ ref('stg_servicing') }} n
join {{ ref('stg_servicing') }} d on d.borrower_id = n.borrower_id and d.status = 'NOD'
where n.status = 'NOS' and n.event_time < d.event_time + to_days(20)
