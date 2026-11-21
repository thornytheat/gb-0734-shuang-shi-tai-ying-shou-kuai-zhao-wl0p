from collections import Counter

from app.errors import Problem
from app.evidence import digest
from app.records import Intake
from app.store import Store
from app.modules.m1_intake.axis import source_ticks
from app.modules.m1_intake.reader import read


def summarize(source_id: str, data: Intake):
    return {
        "source_id": source_id, "encoding": data.encoding,
        "counts": {"input": data.input_rows, "accepted": len(data.events), "quarantine": len(data.quarantine),
                   "duplicates": len(data.duplicates), "blank": data.blanks, "repeated_headers": data.headers},
        "reason_counts": dict(Counter(item["code"] for item in data.quarantine)),
        "quarantine": data.quarantine, "duplicates": data.duplicates, "axis": source_ticks(data.events),
    }


def ingest(store: Store, content: bytes):
    data = read(content)
    source_id = digest(content)
    with store.connect() as connection:
        connection.execute("INSERT OR IGNORE INTO sources VALUES (?, ?)", (source_id, content))
    return summarize(source_id, data)


def load(store: Store, source_id: str) -> Intake:
    with store.connect() as connection:
        row = connection.execute("SELECT content FROM sources WHERE source_id=?", (source_id,)).fetchone()
    if row is None:
        raise Problem("SOURCE_NOT_FOUND", "收件记录不存在", 404)
    return read(row["content"])
