from bisect import bisect_right
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from app.records import Event
from app.reasons import reason


@dataclass
class VersionBook:
    visible: dict[str, Event] = field(default_factory=dict)
    accepted_versions: dict[str, Event] = field(default_factory=dict)
    active_by_invoice: dict[str, list[Event]] = field(default_factory=lambda: defaultdict(list))
    starts: dict[str, list[date]] = field(default_factory=dict)
    replaced_by: dict[str, Event] = field(default_factory=dict)
    rejected: list[dict] = field(default_factory=list)

    def active(self, invoice: str, day: date) -> Event | None:
        index = bisect_right(self.starts.get(invoice, ()), day) - 1
        if index < 0:
            return None
        event = self.active_by_invoice[invoice][index]
        return event if event.active(day) else None

    def reject(self, event: Event, code: str, related: list[Event] | tuple = ()):
        self.rejected.append({"event": event.public(), **reason(code),
                              "related_count": len(related),
                              "related": [item.public() for item in sorted(related, key=lambda item: item.event_id)[:5]]})
