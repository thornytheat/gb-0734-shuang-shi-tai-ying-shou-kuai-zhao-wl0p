from app.modules.m3_snapshot.service import snapshot
from app.modules.m4_aging.service import age
from app.modules.m5_backfill.service import compare_opening
from app.modules.m6_bridge.bucket_flow import flows
from app.modules.m6_bridge.ledger import change, lines, reconcile


def period_book(data, period):
    opening, restated, late = compare_opening(data, period)
    closing = snapshot(data, period.closing)
    rows = lines(opening, restated, closing)
    buckets = flows(rows, period)
    total = reconcile(opening["totals"]["balance_cents"], closing["totals"]["balance_cents"],
                      change(opening["totals"], closing["totals"]))
    late_parts = change(opening["totals"], restated["totals"])
    period_parts = change(restated["totals"], closing["totals"])
    aging = age(closing)
    migration_total = sum(row["migration_cents"] for row in buckets)
    aging_total = sum(row["closing_cents"] for row in buckets)
    bucket_match = {row["bucket"]: row["closing_cents"] for row in buckets} == {
        row["bucket"]: row["balance_cents"] for row in aging["buckets"]
    }
    success = (bucket_match and total["difference_cents"] == aging["difference_cents"] == migration_total == 0
               and aging_total == total["closing_cents"]
               and all(row["difference_cents"] == 0 for row in buckets)
               and all(row["reconciliation"]["difference_cents"] == 0 for row in rows))
    return {"bridge": {"period": period.public(), "status": "MATCHED" if success else "DIFFERENCE",
                       "totals": total, "late": late_parts, "in_period": period_parts, "buckets": buckets,
                       "migration_net_cents": migration_total, "aging_total_cents": aging_total, "invoices": rows},
            "opening": opening, "restated_opening": restated, "closing": closing, "aging": aging, "backfill": late}
