import json

from app.errors import Problem

FIELDS = "run_id, source_id, rule_version, generated_at, elapsed_ms, result_digest"


def get(connection, run_id):
    row = connection.execute(f"SELECT {FIELDS}, payload FROM archives WHERE run_id=?", (run_id,)).fetchone()
    if row is None:
        raise Problem("RUN_NOT_FOUND", "归档记录不存在", 404)
    return {"manifest": {key: row[key] for key in row.keys() if key != "payload"}, "result": json.loads(row["payload"])}


def insert(connection, manifest, payload):
    values = tuple(manifest[field.strip()] for field in FIELDS.split(","))
    cursor = connection.execute(f"INSERT INTO archives ({FIELDS}, payload) VALUES (?, ?, ?, ?, ?, ?, ?) "
                                "ON CONFLICT(run_id) DO NOTHING", (*values, payload))
    return cursor.rowcount == 1


def history(connection, source_id):
    rows = connection.execute(f"SELECT {FIELDS} FROM archives WHERE (? IS NULL OR source_id=?) "
                              "ORDER BY generated_at DESC, run_id LIMIT 100", (source_id, source_id))
    return [dict(row) for row in rows]
