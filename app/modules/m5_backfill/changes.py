from app.modules.m3_snapshot.service import ACCOUNT


def index_evidence(snapshot):
    states = {}
    for invoice in snapshot["invoices"]:
        event = invoice["version"]
        states[event["line"]] = {"event": event, "state": "ACTIVE_VERSION"}
        for row in invoice["movements"]:
            states[row["event"]["line"]] = {**row, "state": "APPLIED"}
    for key, status in (("pending", "PENDING"), ("quarantine", "QUARANTINED"), ("inactive", "INACTIVE")):
        for row in snapshot[key]:
            if row["event"]["effective"] <= snapshot["cut"]["effective"]:
                states[row["event"]["line"]] = {**row, "state": status}
    return states


def changed_events(before, after):
    former, later = index_evidence(before), index_evidence(after)
    changes = []
    for key in sorted(former.keys() | later.keys()):
        left, right = former.get(key), later.get(key)
        if left == right:
            continue
        event = (right or left)["event"]
        changes.append({"event": event, "before": left, "after": right})
    return changes


def invoice_adjustments(before, after):
    former = {row["invoice_id"]: row for row in before["invoices"]}
    later = {row["invoice_id"]: row for row in after["invoices"]}
    result = []
    for key in sorted(former.keys() | later.keys()):
        left, right = former.get(key), later.get(key)
        if left == right:
            continue
        result.append({"invoice_id": key, "before": left, "after": right,
                       "delta": {field: (right or {}).get(field, 0) - (left or {}).get(field, 0) for field in ACCOUNT}})
    return result
