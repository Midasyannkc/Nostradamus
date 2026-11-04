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

    def _published(self):
        """Batch ids and event ids already in bronze, loaded once and kept current."""
        if not hasattr(self, "_batches"):
            t = self.table("bronze.events")
            self._batches = {sn.summary.additional_properties.get("nostra.batch_id") for sn in t.snapshots() if sn.summary}
            self._ids = set(t.scan(selected_fields=("event_id",)).to_arrow().column("event_id").to_pylist())
        return self._batches, self._ids

    def publish(self, batch_id: str, events: list[dict]) -> str:
        """Write-audit-publish. Stage the batch in its own Iceberg table, audit it, then append it to bronze.

        Returns "published" or "skipped" (this batch id was already published). Raises AuditFailed and leaves bronze
        untouched when the staged batch fails an audit."""
        import json
        from datetime import datetime as dt
        batches, ids = self._published()
        if batch_id in batches:
            return "skipped"
        ing = now()
        rows = [{"event_id": e["event_id"], "event_type": e["event_type"], "schema_version": e["schema_version"],
                 "event_time": dt.fromisoformat(e["event_time"]), "borrower_id": e["borrower_id"], "source": e["source"],
                 "payload": json.dumps(e["payload"]), "batch_id": batch_id, "ingested_at": ing} for e in events]
        if not rows:
            return "published"
        self.cat.create_namespace_if_not_exists("stage")
        name = f"stage.b_{batch_id}"
        if self.cat.table_exists(name):
            self.cat.drop_table(name)
        stage = self.cat.create_table(name, schema=SCHEMAS["bronze.events"])
        try:
            stage.append(pa.Table.from_pylist(rows, schema=SCHEMAS["bronze.events"]))
            staged = self.cat.load_table(name).scan().to_arrow()
            problems = self.audit(staged, len(rows), ids)
            if problems:
                raise AuditFailed(f"batch {batch_id} failed audit: {'; '.join(problems)}")
            self.table("bronze.events").append(staged, snapshot_properties={"nostra.batch_id": batch_id})
            batches.add(batch_id)
            ids.update(staged.column("event_id").to_pylist())
            return "published"
        finally:
            self.cat.drop_table(name)

    @staticmethod
    def audit(staged, expected_rows: int, published_ids: set) -> list[str]:
        problems = []
        if staged.num_rows != expected_rows:
            problems.append(f"row count {staged.num_rows} != {expected_rows}")
        for col in ("event_id", "borrower_id", "event_time"):
            if staged.column(col).null_count:
                problems.append(f"null {col}")
        batch_ids = staged.column("event_id").to_pylist()
        if len(set(batch_ids)) != len(batch_ids):
            problems.append("duplicate event ids inside the batch")
        if published_ids.intersection(batch_ids):
            problems.append("event ids already published")
        return problems


class AuditFailed(ValueError):
    pass
