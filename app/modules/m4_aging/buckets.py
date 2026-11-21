from datetime import date

BUCKETS = {"current": "未逾期", "d01_30": "1–30 天", "d31_60": "31–60 天",
           "d61_90": "61–90 天", "d91_plus": "91 天以上"}


def bucket(overdue_days: int) -> str:
    if overdue_days <= 0:
        return "current"
    if overdue_days <= 30:
        return "d01_30"
    if overdue_days <= 60:
        return "d31_60"
    if overdue_days <= 90:
        return "d61_90"
    return "d91_plus"


def band_at(due: str, effective: date) -> str:
    return bucket((effective - date.fromisoformat(due)).days)
