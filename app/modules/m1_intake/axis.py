from collections import Counter

from app.clock import utc_text


def source_ticks(events):
    effective, known = Counter(), Counter()
    for event in events:
        effective[event.effective.isoformat()] += 1
        known[utc_text(event.known)] += 1
    return {name: [{"at": stamp, "count": count} for stamp, count in sorted(axis.items())]
            for name, axis in (("effective", effective), ("known", known))}
