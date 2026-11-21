import csv
import io
from dataclasses import replace

from app.config import MAX_BYTES, MAX_ROWS
from app.errors import Problem
from app.reasons import reason
from app.records import Intake
from app.modules.m1_intake.contract import COLUMNS, RowError, normalize


def decode(content: bytes):
    if len(content) > MAX_BYTES:
        raise Problem("FILE_TOO_LARGE", "文件须小于或等于 2 MiB", 413)
    if not content:
        raise Problem("EMPTY_FILE", "文件为零字节")
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            text = content.decode(encoding)
        except UnicodeDecodeError:
            continue
        if "\0" not in text:
            return text, encoding
    raise Problem("INVALID_ENCODING", "请使用 UTF-8 或 GB18030 文本")


def isolate(line, raw, code, event_id=None):
    return {"line": line, "event_id": event_id, "raw": raw, **reason(code)}


def read(content: bytes) -> Intake:
    text, encoding = decode(content)
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    result = Intake(encoding, [], [], [], 0, 0, 0)
    header = None
    candidates = {}
    try:
        while True:
            line = reader.line_num + 1
            raw = next(reader, None)
            if raw is None:
                break
            names = tuple(piece.strip().lstrip("\ufeff") for piece in raw)
            if header is None:
                if not any(names):
                    continue
                if len(names) != len(COLUMNS) or set(names) != set(COLUMNS):
                    raise Problem("INVALID_HEADER", f"第 {line} 行缺列、重列或包含未知列")
                header = names
                continue
            result.input_rows += 1
            if result.input_rows > MAX_ROWS:
                raise Problem("TOO_MANY_ROWS", "最多接收 5000 条表头后记录", 413)
            if not any(names):
                result.blanks += 1
            elif names == header:
                result.headers += 1
            elif len(raw) != len(header):
                result.quarantine.append(isolate(line, raw, "ROW_WIDTH"))
            else:
                row = dict(zip(header, raw))
                try:
                    event = normalize(line, row)
                    candidates.setdefault((event.event_id, event.known), []).append((event, row))
                except RowError as exc:
                    result.quarantine.append(isolate(line, row, str(exc), row["event_id"]))
    except csv.Error as exc:
        raise Problem("MALFORMED_CSV", f"第 {line} 行 CSV 记录损坏") from exc
    if header is None:
        raise Problem("BLANK_FILE", "文件仅包含空行")
    if result.input_rows == result.headers + result.blanks:
        raise Problem("NO_RECORDS", "表头后没有业务记录")
    for (event_id, _), rows in candidates.items():
        first = rows[0][0]
        if any(replace(event, line=first.line) != first for event, _ in rows[1:]):
            result.quarantine.extend(isolate(event.line, row, "EVENT_ID_CONFLICT", event_id) for event, row in rows)
        else:
            result.events.append(first)
            result.duplicates.extend(isolate(event.line, row, "DUPLICATE_EVENT", event_id) for event, row in rows[1:])
    result.events.sort(key=lambda item: item.line)
    result.quarantine.sort(key=lambda item: item["line"])
    result.duplicates.sort(key=lambda item: item["line"])
    return result
