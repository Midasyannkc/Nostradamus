import os

from nostradamus.lake import Lake
from nostradamus.log import Consumer, Log, Producer
from nostradamus.processor import Processor
from nostradamus.state import State

B = "B000001"


def ev(kind, t, payload, eid, b=B, version=1):
    return {"event_id": eid, "event_type": kind, "schema_version": version, "event_time": t, "borrower_id": b,
            "source": "test", "payload": payload}


def pay(eid, t, dpd=0, b=B, paid=100.0):
    return ev("payment", t, {"due_date": t[:7] + "-01", "amount_due": 100.0, "amount_paid": paid, "days_past_due": dpd}, eid, b)


def overdraft(eid, t, b=B, amount=50.0):
    return ev("overdraft", t, {"account_id": "A1", "amount": amount, "balance_after": -10.0, "fee": 35.0}, eid, b)


def harness(tmp_path, group="g", statics=None, model=None):
    log = Log(os.path.join(tmp_path, "log"))
    lake = Lake(os.path.join(tmp_path, "lake"))
    prod = Producer(log)
    statics = statics or {B: {"ltv": .8, "dti": .35, "area_risk": 0.0}}
    proc = Processor(Consumer(log, "events", group), State(), statics, lake, model=model)
    return log, lake, prod, proc


def send(prod, events):
    for e in events:
        prod.append("events", e.get("borrower_id") or "unknown", e)
    prod.flush()


def drain(proc):
    while proc.run_batch():
        pass
