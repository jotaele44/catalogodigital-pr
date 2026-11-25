"""Bounded RFC3339 timestamp profile; no fabricated calendar precision."""
import re
from datetime import datetime, timezone
from jsonschema import FormatChecker

_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})", re.ASCII)

def parse_timestamp(value):
    if not isinstance(value, str) or not _PATTERN.fullmatch(value):
        raise ValueError("explicit offset and calendar timestamp required")
    if value.endswith("-00:00"):
        raise ValueError("unknown offset is outside bounded profile")
    if not value.endswith("Z"):
        hours, minutes = map(int, value[-5:].split(":"))
        if hours > 23 or minutes > 59:
            raise ValueError("invalid offset")
    return datetime.fromisoformat(value.replace("Z","+00:00")).astimezone(timezone.utc)

def checker():
    result = FormatChecker()
    @result.checks("date-time", raises=(ValueError, OverflowError))
    def valid(value):
        if isinstance(value, str):
            parse_timestamp(value)
        return True
    return result

def validate_temporal(record):
    start, end = record["start"], record["end"]
    precision = record["precision"]
    a = parse_timestamp(start) if start is not None else None
    b = parse_timestamp(end) if end is not None else None
    if precision == "UNKNOWN":
        if a is not None or b is not None:
            raise ValueError("unknown precision cannot assert normalized bounds")
    elif precision == "INSTANT":
        if a is None or (b is not None and a != b):
            raise ValueError("instant requires one point")
    elif precision == "INTERVAL":
        if a is None and b is None:
            raise ValueError("interval requires at least one bound")
    else:
        raise ValueError("coarse calendar precision requires a separate future contract")
    if a is not None and b is not None and a > b:
        raise ValueError("reversed interval")
    return True
