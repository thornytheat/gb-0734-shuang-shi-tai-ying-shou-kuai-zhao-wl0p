from collections import defaultdict
from itertools import groupby

from app.modules.m2_versions.book import VersionBook


def overlaps(left, right):
    return ((left.valid_to is None or right.effective < left.valid_to)
            and (right.valid_to is None or left.effective < right.valid_to))


def apply_versions(book, invoice, cohort):
    current = book.active_by_invoice[invoice]
    customer = current[0].customer_id if current else None
    if customer is None and len({item.customer_id for item in cohort}) > 1:
        for item in cohort:
            book.reject(item, "CUSTOMER_CONFLICT")
        return
    roots = []
    revisions = defaultdict(list)
    by_id = {item.event_id: item for item in current}
    for item in cohort:
        if customer is not None and item.customer_id != customer:
            book.reject(item, "CUSTOMER_CONFLICT", current[:1])
        elif not item.ref:
            roots.append(item)
        elif item.ref not in by_id:
            parent = book.accepted_versions.get(item.ref)
            code = "VERSION_SCOPE" if parent and parent.known < item.known and parent.invoice_id != invoice else "VERSION_PARENT"
            book.reject(item, code, [parent] if parent and parent.known < item.known else [])
        else:
            parent = by_id[item.ref]
            if (item.effective, item.valid_to) != (parent.effective, parent.valid_to):
                book.reject(item, "VERSION_SCOPE", [parent])
            else:
                revisions[parent].append(item)
    for parent, siblings in revisions.items():
        if len(siblings) > 1:
            for item in siblings:
                book.reject(item, "VERSION_FORK", [parent, *(other for other in siblings if other != item)])
            continue
        replacement = siblings[0]
        current[current.index(parent)] = replacement
        book.accepted_versions[replacement.event_id] = replacement
        book.replaced_by[parent.event_id] = replacement
    eligible = []
    for item in roots:
        collisions = [other for other in current if overlaps(item, other)]
        if collisions:
            book.reject(item, "INTERVAL_OVERLAP", collisions)
        else:
            eligible.append(item)
    for item in eligible:
        collisions = [other for other in eligible if item != other and overlaps(item, other)]
        if collisions:
            book.reject(item, "INTERVAL_OVERLAP", collisions)
        else:
            current.append(item)
            book.accepted_versions[item.event_id] = item
    current.sort(key=lambda item: item.effective)
    book.starts[invoice] = [item.effective for item in current]


def build(events, known):
    book = VersionBook()
    ordered = sorted((event for event in events if event.known <= known),
                     key=lambda event: (event.known, event.event_id, event.line))
    for _, group in groupby(ordered, key=lambda event: event.known):
        invoices = defaultdict(list)
        for event in group:
            if event.event_id in book.visible:
                book.reject(event, "EVENT_ID_CONFLICT", [book.visible[event.event_id]])
                continue
            book.visible[event.event_id] = event
            if event.kind == "VERSION":
                invoices[event.invoice_id].append(event)
        for invoice, cohort in sorted(invoices.items()):
            apply_versions(book, invoice, cohort)
    return book
