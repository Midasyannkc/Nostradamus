"""Event envelope and payload fields."""
ENVELOPE = ("event_id", "event_type", "schema_version", "event_time", "borrower_id", "source", "payload")
PAYLOAD = {
    "payment": ("due_date", "amount_due", "amount_paid", "days_past_due"),
    "overdraft": ("account_id", "amount", "balance_after", "fee"),
    "credit_snapshot": ("score", "utilization", "accounts_closed_12m", "new_accounts_90d", "inquiries_90d",
                        "other_tradeline_late_30d"),
    "alt_signal": ("overspend_index", "household_loan_count", "household_monthly_debt", "lien_judgment_count",
                   "address_changes_12m"),
    "servicing_status": ("status",),
}
