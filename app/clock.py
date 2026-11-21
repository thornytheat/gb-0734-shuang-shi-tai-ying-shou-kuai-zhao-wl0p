import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import Depends
from pydantic import BaseModel

from app.errors import Problem

DAY = re.compile(r"\d{4}-\d{2}-\d{2}", re.ASCII)
INSTANT = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:[0-5]\d)", re.ASCII)


def parse_day(value: str) -> date:
    if not DAY.fullmatch(value):
        raise ValueError("日期须为 YYYY-MM-DD")
    return date.fromisoformat(value)


def parse_known(value: str) -> datetime:
    if not INSTANT.fullmatch(value) or value.endswith("-00:00"):
        raise ValueError("知悉截止须带明确时区偏移")
    try:
        return datetime.fromisoformat(value).astimezone(timezone.utc)
    except (OverflowError, ValueError) as exc:
        raise ValueError("知悉时间超出范围") from exc


def utc_text(value: datetime) -> str:
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class Cut:
    effective: date
    known: datetime

    def public(self):
        return {"effective": self.effective.isoformat(), "known": utc_text(self.known)}


@dataclass(frozen=True)
class Period:
    opening: Cut
    closing: Cut

    def __post_init__(self):
        if self.opening.effective >= self.closing.effective or self.opening.known > self.closing.known:
            raise Problem("INVALID_PERIOD", "期初有效日须早于期末，知悉截止须顺序排列")

    def public(self):
        return {"opening": self.opening.public(), "closing": self.closing.public()}


def cut_query(effective: str, known: str) -> Cut:
    try:
        return Cut(parse_day(effective), parse_known(known))
    except ValueError as exc:
        raise Problem("INVALID_CUT", str(exc)) from exc


def period_query(open_effective: str, open_known: str, effective: str, known: str) -> Period:
    return Period(cut_query(open_effective, open_known), cut_query(effective, known))


CutQuery = Annotated[Cut, Depends(cut_query)]
PeriodQuery = Annotated[Period, Depends(period_query)]


class ArchiveRequest(BaseModel):
    source_id: str
    open_effective: str
    open_known: str
    effective: str
    known: str

    def period(self):
        return period_query(self.open_effective, self.open_known, self.effective, self.known)
