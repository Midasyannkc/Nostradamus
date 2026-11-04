"""Apache Iceberg tables (pyiceberg, SQL catalog on SQLite, local warehouse) for bronze events and gold outputs."""
import os
from datetime import datetime, timezone

import pyarrow as pa
from pyiceberg.catalog.sql import SqlCatalog

TS = pa.timestamp("us", tz="UTC")
SCHEMAS = {
    "bronze.events": pa.schema([("event_id", pa.string()), ("event_type", pa.string()), ("schema_version", pa.int32()),
                                ("event_time", TS), ("borrower_id", pa.string()), ("source", pa.string()),
                                ("payload", pa.string()), ("batch_id", pa.string()), ("ingested_at", TS)]),
    "bronze.dead_letter": pa.schema([("raw", pa.string()), ("reason", pa.string()), ("batch_id", pa.string()),
                                     ("ingested_at", TS)]),
    "gold.alerts": pa.schema([("alert_id", pa.string()), ("borrower_id", pa.string()), ("as_of_month", pa.int32()),
                              ("alert_time", TS), ("score", pa.float64()), ("reasons", pa.string()),
                              ("model_version", pa.string())]),
}


def now():
    return datetime.now(timezone.utc)


class Lake:
    def __init__(self, root: str):
        os.makedirs(root, exist_ok=True)
        self.root = root
        self.cat = SqlCatalog("nostradamus", uri=f"sqlite:///{root}/catalog.db", warehouse=f"file://{root}/warehouse")
        for ns in ("bronze", "gold"):
            self.cat.create_namespace_if_not_exists(ns)
        for name, schema in SCHEMAS.items():
            self.cat.create_table_if_not_exists(name, schema=schema)

    def table(self, name):
        return self.cat.load_table(name)

    def append(self, name: str, rows: list[dict], props: dict | None = None):
        if not rows:
            return
        t = pa.Table.from_pylist(rows, schema=SCHEMAS[name])
        self.table(name).append(t, snapshot_properties=props or {})

    def rows(self, name: str):
        return self.table(name).scan().to_arrow().to_pylist()

    def count(self, name: str) -> int:
        return self.table(name).scan().to_arrow().num_rows

    def publish(self, batch_id: str, events: list[dict]):
        """Append one batch of validated events to the bronze table."""
        from datetime import datetime as dt
        ing = now()
        rows = [{"event_id": e["event_id"], "event_type": e["event_type"], "schema_version": e["schema_version"],
                 "event_time": dt.fromisoformat(e["event_time"]), "borrower_id": e["borrower_id"], "source": e["source"],
                 "payload": __import__("json").dumps(e["payload"]), "batch_id": batch_id, "ingested_at": ing}
                for e in events]
        self.append("bronze.events", rows, {"nostra.batch_id": batch_id})
