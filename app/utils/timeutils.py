from datetime import datetime, time, timedelta

def parse_hhmm(s: str) -> time:
    hh, mm = s.split(":")
    return time(int(hh), int(mm))

def compute_lateness(now: datetime, start_hhmm: str, grace_min: int) -> int:
    start = parse_hhmm(start_hhmm)
    limit = datetime.combine(now.date(), start) + timedelta(minutes=grace_min)
    return max(0, int((now - limit).total_seconds() // 60))
