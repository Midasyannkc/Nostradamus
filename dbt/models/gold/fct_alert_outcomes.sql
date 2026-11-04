-- One row per alerted borrower: first alert, the notice of sale if one followed, lead time and the horizon outcome.
with first_alert as (
    select borrower_id, min(alert_time) as first_alert_time, count(*) as alerts
    from {{ ref('stg_alerts') }} group by 1
),
nos as (
    select borrower_id, min(event_time) as nos_time from {{ ref('stg_servicing') }} where status = 'NOS' group by 1
)
select a.borrower_id, d.city, d.focus, a.first_alert_time, cast(a.first_alert_time as date) as alert_date, a.alerts, n.nos_time,
       coalesce(n.nos_time > a.first_alert_time, false) as flagged_before_notice,
       case when n.nos_time > a.first_alert_time then date_diff('second', a.first_alert_time, n.nos_time) / 86400.0 end as lead_days,
       a.first_alert_time + to_days({{ var('horizon_days') }}) <= timestamptz '{{ var('data_end') }}' as matured,
       coalesce(n.nos_time > a.first_alert_time and n.nos_time <= a.first_alert_time + to_days({{ var('horizon_days') }}), false) as hit
from first_alert a
left join nos n using (borrower_id)
left join {{ ref('dim_borrower') }} d using (borrower_id)
