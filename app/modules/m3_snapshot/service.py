from app.modules.m2_versions.rules import build
from app.modules.m3_snapshot.movements import evaluate

ACCOUNT = ("face_cents", "receipts_cents", "reversed_cents", "balance_cents")


def snapshot(data, cut):
    book = build(data.events, cut.known)
    selected = {}
    for invoice in sorted(book.active_by_invoice):
        version = book.active(invoice, cut.effective)
        if version is not None:
            selected[invoice] = version
    applied, pending, movement_rejects, inactive = evaluate(book, cut.effective, selected)
    invoices = []
    for invoice, version in selected.items():
        moves = applied[invoice]
        receipts = sum(row["event"]["amount_cents"] for row in moves if row["event"]["kind"] == "PAYMENT")
        reversed_cents = sum(row["event"]["amount_cents"] for row in moves if row["event"]["kind"] == "REVERSAL")
        invoices.append({"invoice_id": invoice, "customer_id": version.customer_id, "due": version.due.isoformat(),
                         "version": version.public(), "movements": moves, "face_cents": version.cents,
                         "receipts_cents": receipts, "reversed_cents": reversed_cents,
                         "balance_cents": version.cents - receipts - reversed_cents})
    totals = {key: sum(row[key] for row in invoices) for key in ACCOUNT}
    return {"cut": cut.public(), "invoices": invoices, "totals": totals,
            "pending": pending, "quarantine": book.rejected + movement_rejects, "inactive": inactive}
