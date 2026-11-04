-- Outcome KPIs for the live window, computed in SQL. Reconciled to the Python evaluation.
with live_nos as (
    select borrower_id, min(event_time) as nos_time
    from {{ ref('stg_servicing') }} where status = 'NOS' group by 1
    having min(event_time) >= timestamptz '{{ var('live_start') }}' and min(event_time) < timestamptz '{{ var('data_end') }}'
),
caught as (
    select l.borrower_id, f.lead_days
    from live_nos l join {{ ref('fct_alert_outcomes') }} f using (borrower_id)
    where f.first_alert_time < l.nos_time
)
select 'live_notices_of_sale' as metric, (select count(*) from live_nos)::double as value
union all select 'caught_before_notice', (select count(*) from caught)::double
union all select 'recall', round((select count(*) from caught) * 1.0 / (select count(*) from live_nos), 4)
union all select 'alerted_borrowers', (select count(*) from {{ ref('fct_alert_outcomes') }})::double
union all select 'mature_alerted_borrowers', (select count(*) from {{ ref('fct_alert_outcomes') }} where matured)::double
union all select 'hits_within_horizon', (select count(*) from {{ ref('fct_alert_outcomes') }} where matured and hit)::double
union all select 'precision', round((select count(*) from {{ ref('fct_alert_outcomes') }} where matured and hit) * 1.0 /
                                    (select count(*) from {{ ref('fct_alert_outcomes') }} where matured), 4)
union all select 'median_lead_days', round((select median(lead_days) from caught), 1)
