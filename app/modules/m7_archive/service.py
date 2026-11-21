import sqlite3
from datetime import datetime, timezone
from time import perf_counter_ns

from app.clock import period_query, utc_text
from app.config import RULE_VERSION
from app.errors import Problem
from app.evidence import canonical, digest
from app.modules.m1_intake.service import load, summarize
from app.modules.m6_bridge.service import period_book
from app.modules.m7_archive import repository


def read_run(store, run_id):
    with store.connect() as connection:
        return repository.get(connection, run_id)


def save(store, source_id, period):
    start = perf_counter_ns()
    inputs = {"source_id": source_id, "rule_version": RULE_VERSION, "period": period.public()}
    run_id = digest(canonical(inputs))
    data = load(store, source_id)
    result = {"intake": summarize(source_id, data), **period_book(data, period)}
    if result["bridge"]["status"] != "MATCHED":
        raise Problem("UNBALANCED", "期间桥接存在差额", 409)
    payload = canonical(result)
    manifest = {"run_id": run_id, "source_id": source_id, "rule_version": RULE_VERSION,
                "elapsed_ms": (perf_counter_ns() - start) // 1_000_000,
                "generated_at": utc_text(datetime.now(timezone.utc)), "result_digest": digest(payload)}
    try:
        with store.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            created = repository.insert(connection, manifest, payload)
            stored = repository.get(connection, run_id)
            if (stored["manifest"]["result_digest"] != manifest["result_digest"]
                    or digest(canonical(stored["result"])) != manifest["result_digest"]):
                raise Problem("ARCHIVE_MISMATCH", "重算摘要与归档不符", 409)
    except sqlite3.Error as exc:
        raise Problem("ARCHIVE_WRITE_FAILED", "归档写入失败，请重跑", 503) from exc
    return {"created": created, "manifest": stored["manifest"], "period": period.public(),
            "totals": result["bridge"]["totals"]}


def rerun(store, run_id):
    stored = read_run(store, run_id)
    if stored["manifest"]["rule_version"] != RULE_VERSION:
        raise Problem("RULE_VERSION_CHANGED", "归档使用的规则版本已变更", 409)
    period = stored["result"]["bridge"]["period"]
    opening, closing = period["opening"], period["closing"]
    cuts = period_query(opening["effective"], opening["known"], closing["effective"], closing["known"])
    candidate = digest(canonical({"source_id": stored["manifest"]["source_id"], "rule_version": RULE_VERSION,
                                  "period": cuts.public()}))
    if candidate != run_id:
        raise Problem("ARCHIVE_MISMATCH", "归档参数与运行编号不符", 409)
    return save(store, stored["manifest"]["source_id"], cuts)
