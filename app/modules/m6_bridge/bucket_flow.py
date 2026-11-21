from app.modules.m4_aging.buckets import BUCKETS, band_at


def position(row, day):
    return (band_at(row["due"], day), row["balance_cents"]) if row else (None, 0)


def flows(rows, period):
    totals = {key: dict(bucket=key, label=label, opening_cents=0, late_cents=0,
                        migration_cents=0, period_cents=0, closing_cents=0) for key, label in BUCKETS.items()}
    for row in rows:
        before, restated, close = row["opening"], row["restated"], row["closing"]
        old_key, old_amount = position(before, period.opening.effective)
        late_key, late_amount = position(restated, period.opening.effective)
        end_key, end_amount = position(close, period.closing.effective)
        # At close use the closing due date when present, or age the retiring balance to the close date.
        aged_key = end_key or (band_at(restated["due"], period.closing.effective) if restated else None)
        if old_key:
            totals[old_key]["opening_cents"] += old_amount
            totals[old_key]["late_cents"] -= old_amount
        if late_key:
            totals[late_key]["late_cents"] += late_amount
            totals[late_key]["migration_cents"] -= late_amount
            totals[aged_key]["migration_cents"] += late_amount
        if aged_key:
            totals[aged_key]["period_cents"] += end_amount - late_amount
        if end_key:
            totals[end_key]["closing_cents"] += end_amount
        row["bucket_path"] = {"opening": old_key, "restated": late_key, "aged_to": aged_key, "closing": end_key}
    for record in totals.values():
        record["difference_cents"] = record["closing_cents"] - sum(record[key] for key in (
            "opening_cents", "late_cents", "migration_cents", "period_cents"))
    return list(totals.values())
