"""NostraLog: a small durable, partitioned, append-only log with offsets and consumer groups.

It stands in for Kafka, Azure Event Hubs or Kinesis (no broker could be installed in the build sandbox). Records are
JSON lines in one file per partition, a record's offset is its line number, and a consumer group stores the offset and
byte position it has read up to."""
import json
import os
import time
import zlib
from dataclasses import dataclass

from .config import PARTITIONS


@dataclass
class Record:
    partition: int
    offset: int
    ts: float          # append time, seconds since epoch (processing time)
    key: str
    value: dict


class Log:
    def __init__(self, root: str, partitions: int = PARTITIONS):
        self.root, self.partitions = root, partitions
        os.makedirs(root, exist_ok=True)

    def path(self, topic: str, p: int) -> str:
        d = os.path.join(self.root, topic)
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, f"part-{p}.ndjson")


class Producer:
    def __init__(self, log: Log):
        self.log, self.fh, self.next = log, {}, {}

    def _open(self, topic, p):
        k = (topic, p)
        if k not in self.fh:
            path = self.log.path(topic, p)
            self.next[k] = sum(1 for _ in open(path, "rb")) if os.path.exists(path) else 0
            self.fh[k] = open(path, "ab")
        return k

    def append(self, topic: str, key: str, value: dict) -> tuple[int, int]:
        p = zlib.crc32(str(key).encode()) % self.log.partitions
        k = self._open(topic, p)
        off = self.next[k]
        self.next[k] += 1
        self.fh[k].write((json.dumps({"o": off, "ts": time.time(), "k": key, "v": value}) + "\n").encode())
        return p, off

    def flush(self):
        for fh in self.fh.values():
            fh.flush()

    def close(self):
        self.flush()
        for fh in self.fh.values():
            fh.close()


class Consumer:
    def __init__(self, log: Log, topic: str, group: str):
        self.log, self.topic, self.group = log, topic, group
        self.dir = os.path.join(log.root, "_offsets", group)
        os.makedirs(self.dir, exist_ok=True)

    def _state(self, p):
        f = os.path.join(self.dir, f"{self.topic}-{p}.json")
        return json.load(open(f)) if os.path.exists(f) else {"offset": 0, "pos": 0}

    def _save(self, p, st):
        f = os.path.join(self.dir, f"{self.topic}-{p}.json")
        with open(f + ".tmp", "w") as fh:
            json.dump(st, fh)
        os.replace(f + ".tmp", f)

    def poll(self, max_records: int = 5000) -> list[Record]:
        out = []
        per = max(1, max_records // self.log.partitions)
        for p in range(self.log.partitions):
            path = self.log.path(self.topic, p)
            if not os.path.exists(path):
                continue
            st = self._state(p)
            with open(path, "rb") as fh:
                fh.seek(st["pos"])
                n = 0
                while n < per:
                    line = fh.readline()
                    if not line.endswith(b"\n"):        # empty, or a line still being written
                        break
                    d = json.loads(line)
                    out.append(Record(p, d["o"], d["ts"], d["k"], d["v"]))
                    st = {"offset": d["o"] + 1, "pos": fh.tell()}
                    n += 1
            self._save(p, st)                           # auto commit on poll
        return out
