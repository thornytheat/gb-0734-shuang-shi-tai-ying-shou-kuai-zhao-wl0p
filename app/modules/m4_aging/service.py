from datetime import date

from app.modules.m4_aging.buckets import BUCKETS, bucket


def age(snapshot):
    effective = date.fromisoformat(snapshot["cut"]["effective"])
    sums = {key: {"bucket": key, "label": label, "count": 0, "balance_cents": 0} for key, label in BUCKETS.items()}
    lines, cleared = [], 0
    for entry in snapshot["invoices"]:
        if entry["balance_cents"] == 0:
            cleared += 1
            continue
        days = (effective - date.fromisoformat(entry["due"])).days
        key = bucket(days)
        rows = sums[key]
        rows["count"] += 1
        rows["balance_cents"] += entry["balance_cents"]
        lines.append({"invoice_id": entry["invoice_id"], "customer_id": entry["customer_id"], "due": entry["due"],
                      "days_overdue": max(0, days), "bucket": key, "balance_cents": entry["balance_cents"],
                      "version_line": entry["version"]["line"], "event_id": entry["version"]["event_id"]})
    total = sum(row["balance_cents"] for row in sums.values())
    return {"cut": snapshot["cut"], "buckets": list(sums.values()), "invoices": lines, "cleared": cleared,
            "total_cents": total, "overdue_cents": total - sums["current"]["balance_cents"],
            "difference_cents": total - snapshot["totals"]["balance_cents"]}
