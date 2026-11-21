from dataclasses import dataclass
from datetime import date, datetime

from app.clock import utc_text


@dataclass(frozen=True)
class Event:
    line: int
    event_id: str
    invoice_id: str
    customer_id: str
    kind: str
    effective: date
    known: datetime
    cents: int
    valid_to: date | None = None
    due: date | None = None
    ref: str = ""
    note: str = ""

    def active(self, day: date) -> bool:
        return self.effective <= day and (self.valid_to is None or day < self.valid_to)

    def public(self):
        return {
            "line": self.line, "event_id": self.event_id, "invoice_id": self.invoice_id,
            "customer_id": self.customer_id, "kind": self.kind, "effective": self.effective.isoformat(),
            "known": utc_text(self.known), "amount_cents": self.cents,
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "due": self.due.isoformat() if self.due else None, "ref": self.ref, "note": self.note,
        }


@dataclass
class Intake:
    encoding: str
    events: list[Event]
    quarantine: list[dict]
    duplicates: list[dict]
    blanks: int
    headers: int
    input_rows: int
