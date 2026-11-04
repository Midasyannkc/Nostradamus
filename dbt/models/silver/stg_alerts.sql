select alert_id, borrower_id, as_of_month, alert_time, score, reasons, model_version
from {{ source('bronze', 'alerts') }}
