from app.modules.m2_versions.rules import build


def versions_at(data, cut):
    book = build(data.events, cut.known)
    timeline = []
    for version in sorted(book.accepted_versions.values(), key=lambda event: (event.invoice_id, event.effective, event.known)):
        successor = book.replaced_by.get(version.event_id)
        if successor:
            state = "SUPERSEDED"
        elif version.active(cut.effective):
            state = "ACTIVE"
        else:
            state = "OUTSIDE_CUT"
        timeline.append({**version.public(), "state": state,
                         "known_to": successor.public()["known"] if successor else None,
                         "replaced_by": successor.event_id if successor else None})
    return {"cut": cut.public(), "versions": timeline, "quarantine": book.rejected}
