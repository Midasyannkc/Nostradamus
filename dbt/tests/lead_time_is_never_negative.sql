select borrower_id from {{ ref('fct_alert_outcomes') }} where lead_days < 0
