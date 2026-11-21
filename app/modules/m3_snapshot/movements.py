from collections import defaultdict

from app.reasons import reason


def evaluate(book, effective, selected):
    applied = defaultdict(list)
    spent = defaultdict(int)
    pending, rejected, inactive = [], [], []
    movements = sorted((event for event in book.visible.values() if event.kind != "VERSION" and event.effective <= effective),
                       key=lambda item: (item.effective, item.known, item.kind, item.event_id))
    for event in movements:
        target = book.accepted_versions.get(event.ref)
        at_event = book.active(event.invoice_id, event.effective)
        at_cut = selected.get(event.invoice_id)
        row = {"event": event.public(), "target": target.public() if target else None,
               "at_event": at_event.public() if at_event else None}
        if target is None:
            code = "TARGET_INVALID" if event.ref in book.visible else "TARGET_PENDING"
        elif (target.invoice_id, target.customer_id) != (event.invoice_id, event.customer_id) or target.effective > event.effective:
            code = "TARGET_SCOPE"
        elif at_event is None:
            code = "NO_ACTIVE_VERSION"
        elif at_cut is None:
            inactive.append(row)
            continue
        else:
            remaining = min(at_event.cents, at_cut.cents) - spent[event.invoice_id]
            if event.cents <= remaining:
                spent[event.invoice_id] += event.cents
                applied[event.invoice_id].append(row)
                continue
            code = "EXCEEDS_BALANCE"
            row["available_cents"] = max(0, remaining)
        destination = pending if code == "TARGET_PENDING" else rejected
        destination.append({**row, **reason(code)})
    return applied, pending, rejected, inactive
