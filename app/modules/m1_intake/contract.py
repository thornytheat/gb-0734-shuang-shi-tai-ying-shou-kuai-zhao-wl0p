import re
import unicodedata
from decimal import Decimal

from app.clock import parse_day, parse_known
from app.records import Event

COLUMNS = ("event_id", "invoice_id", "customer_id", "kind", "effective", "valid_to", "known",
           "due", "amount_cny", "ref", "note")
KINDS = {"VERSION", "PAYMENT", "REVERSAL"}
NULL_AMOUNT = {"", "-", "N/A", "NULL", "未知"}
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")
AMOUNT = re.compile(r"(?:[0-9]{1,12}|[0-9]{1,3}(?:,[0-9]{3}){1,3})(?:\.[0-9]{1,2})?")
MAX_CENTS = 999_999_999_999


class RowError(ValueError):
    pass


def amount(text: str) -> int:
    value = unicodedata.normalize("NFKC", text).strip()
    if value.upper() in NULL_AMOUNT:
        raise RowError("AMOUNT_MISSING")
    if not AMOUNT.fullmatch(value):
        raise RowError("INVALID_AMOUNT")
    cents = int(Decimal(value.replace(",", "")) * 100)
    if not 0 < cents <= MAX_CENTS:
        raise RowError("INVALID_AMOUNT")
    return cents


def normalize(line: int, row: dict[str, str]) -> Event:
    event_id, invoice, customer, ref = (row[key].strip() for key in ("event_id", "invoice_id", "customer_id", "ref"))
    if not all(ID.fullmatch(value) for value in (event_id, invoice, customer)) or (ref and not ID.fullmatch(ref)):
        raise RowError("INVALID_ID")
    kind = row["kind"].strip().upper()
    if kind not in KINDS:
        raise RowError("UNKNOWN_KIND")
    end_text, due_text = row["valid_to"].strip(), row["due"].strip()
    if (kind == "VERSION" and not due_text) or (kind != "VERSION" and (end_text or due_text or not ref)):
        raise RowError("UNEXPECTED_FIELDS")
    try:
        effective = parse_day(row["effective"].strip())
        valid_to = parse_day(end_text) if end_text else None
        due = parse_day(due_text) if due_text else None
    except ValueError as exc:
        raise RowError("INVALID_DATE") from exc
    if valid_to and valid_to <= effective:
        raise RowError("INVALID_INTERVAL")
    try:
        known = parse_known(row["known"].strip())
    except ValueError as exc:
        raise RowError("INVALID_TIMESTAMP") from exc
    return Event(line, event_id, invoice, customer, kind, effective, known,
                 amount(row["amount_cny"]), valid_to, due, ref, row["note"])
