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


def validate(e: dict) -> str | None:
    """Return None when the event satisfies the contract, otherwise a short reason."""
    from datetime import datetime
    if not isinstance(e, dict):
        return "not_an_object"
    for f in ENVELOPE:
        if f not in e:
            return f"missing_envelope:{f}"
    if not e["borrower_id"] or not isinstance(e["borrower_id"], str):
        return "invalid:borrower_id"
    if e["event_type"] not in PAYLOAD:
        return f"unknown_event_type:{e['event_type']}"
    try:
        datetime.fromisoformat(e["event_time"])
    except Exception:
        return "invalid:event_time"
    if not isinstance(e["payload"], dict):
        return "invalid:payload"
    for f in PAYLOAD[e["event_type"]]:
        if f not in e["payload"]:
            return f"missing_payload:{f}"
    return None


# Field renames that an upstream owner has confirmed. Registering one lets a quarantined event be replayed.
ALIASES = {"payment": {"dpd": "days_past_due"}}


def normalize(e: dict) -> dict:
    """Apply confirmed field aliases to a copy of the event."""
    amap = ALIASES.get(e.get("event_type"), {})
    if not amap or not isinstance(e.get("payload"), dict):
        return e
    p = {amap.get(k, k): v for k, v in e["payload"].items()}
    return {**e, "payload": p}
