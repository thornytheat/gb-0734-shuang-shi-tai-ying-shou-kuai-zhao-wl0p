PARTS = {"posted_cents": "face_cents", "collected_cents": "receipts_cents", "reversed_cents": "reversed_cents"}


def change(start, end):
    return {name: (end or {}).get(key, 0) - (start or {}).get(key, 0) for name, key in PARTS.items()}


def reconcile(opening, closing, parts):
    expected = opening + parts["posted_cents"] - parts["collected_cents"] - parts["reversed_cents"]
    return {"opening_cents": opening, **parts, "closing_cents": closing,
            "expected_cents": expected, "difference_cents": closing - expected}


def lines(opening, restated, closing):
    tables = [{row["invoice_id"]: row for row in item["invoices"]} for item in (opening, restated, closing)]
    rows = []
    for invoice in sorted(tables[0].keys() | tables[1].keys() | tables[2].keys()):
        left, middle, right = (table.get(invoice) for table in tables)
        rows.append({"invoice_id": invoice, "customer_id": (right or middle or left)["customer_id"],
                     "opening": left, "restated": middle, "closing": right,
                     "late": change(left, middle), "period": change(middle, right),
                     "reconciliation": reconcile((left or {}).get("balance_cents", 0),
                                                 (right or {}).get("balance_cents", 0), change(left, right))})
    return rows
