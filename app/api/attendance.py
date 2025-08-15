# F:\PythonProject\face-attendance\app\api\attendance.py

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, date, time, timedelta
import calendar
import os
from typing import Optional, Dict

from app.db.base import get_db
from app.db.models import Employee, Shift, AttendanceLog

# Try to use your helper; provide safe fallbacks if files aren't created yet
try:
    from app.utils.timeutils import compute_lateness
except Exception:
    def compute_lateness(now: datetime, start_hhmm: str, grace_min: int) -> int:
        """Fallback: compute minutes late relative to start_hhmm + grace."""
        hh, mm = map(int, start_hhmm.split(":"))
        limit = datetime.combine(now.date(), time(hh, mm)) + timedelta(minutes=grace_min)
        return max(0, int((now - limit).total_seconds() // 60))

try:
    from app.tts.speak import say  # pyttsx3 based; safe no-op below if missing
except Exception:
    def say(_text: str) -> None:
        pass


router = APIRouter(prefix="/attendance", tags=["attendance"])

SNAP_DIR = "snapshots"
os.makedirs(SNAP_DIR, exist_ok=True)


def get_or_create_default_shift(db: Session) -> Shift:
    """Ensure a default 09:00-17:00 shift with 5 min grace exists."""
    s = db.query(Shift).filter(Shift.name == "Morning").first()
    if s:
        return s
    s = Shift(name="Morning", start_hhmm="09:00", end_hhmm="17:00", grace_minutes=5)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.post("/checkin")
async def checkin(
    emp_code: str = Form(...),
    frame: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """
    Check-in for a known employee code.
    Saves optional snapshot, computes lateness vs default shift, logs an AttendanceLog.
    """
    emp = db.query(Employee).filter(Employee.emp_code == emp_code).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Save snapshot if provided
    snap_path = None
    if frame is not None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"{emp_code}_{ts}.jpg"
        snap_path = os.path.join(SNAP_DIR, fname)
        with open(snap_path, "wb") as f:
            f.write(await frame.read())

    # Shift & lateness
    shift = get_or_create_default_shift(db)
    now = datetime.now()
    late_min = compute_lateness(now, shift.start_hhmm, shift.grace_minutes)
    status = "present-on-time" if late_min == 0 else "late"

    # Log
    log = AttendanceLog(
        employee_id=emp.id,
        ts=now,
        status="present",
        lateness_minutes=late_min,
        snapshot_path=snap_path,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    # Voice + response
    msg = f"{emp.full_name} on time" if status == "present-on-time" \
        else f"{emp.full_name} late by {late_min} minutes"
    say(msg)

    return {
        "ok": True,
        "employee_id": emp.id,
        "status": status,
        "lateness_minutes": late_min,
        "message": msg,
        "log_id": log.id,
        "snapshot_path": snap_path,
    }


@router.get("/today")
def today_logs(db: Session = Depends(get_db)):
    """List today's attendance logs (all employees)."""
    d = date.today()
    start = datetime.combine(d, datetime.min.time())
    # exclusive upper bound
    end = start + timedelta(days=1)
    logs = (
        db.query(AttendanceLog)
        .filter(AttendanceLog.ts >= start, AttendanceLog.ts < end)
        .order_by(AttendanceLog.ts.asc())
        .all()
    )
    return [
        {
            "employee_id": l.employee_id,
            "ts": l.ts.isoformat(),
            "lateness_minutes": l.lateness_minutes,
            "status": l.status,
            "snapshot_path": l.snapshot_path,
        }
        for l in logs
    ]


def _month_bounds(y: int, m: int) -> tuple[datetime, datetime]:
    start_date = date(y, m, 1)
    # first day of next month
    if m == 12:
        next_month = date(y + 1, 1, 1)
    else:
        next_month = date(y, m + 1, 1)
    return datetime.combine(start_date, time.min), datetime.combine(next_month, time.min)


def _business_days_in_month(y: int, m: int) -> int:
    _, last_day = calendar.monthrange(y, m)
    count = 0
    for day in range(1, last_day + 1):
        wd = date(y, m, day).weekday()
        if wd < 5:  # Mon-Fri
            count += 1
    return count


@router.get("/monthly_summary")
def monthly_summary(
    emp_code: str = Query(..., description="Employee code"),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    speak: bool = Query(False, description="If true, device speaks the summary"),
    db: Session = Depends(get_db),
):
    """
    Returns monthly counts:
      - present_days (unique days with any check-in)
      - late_days (unique days with lateness_minutes > 0)
      - total_late_minutes (sum of first check-in lateness per day)
      - working_days (Mon-Fri count in that month)
      - absent_days (working_days - present_days)
    """
    # defaults: current month
    now = datetime.now()
    y = year or now.year
    m = month or now.month

    emp = db.query(Employee).filter(Employee.emp_code == emp_code).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    start_dt, next_month_dt = _month_bounds(y, m)
    logs = (
        db.query(AttendanceLog)
        .filter(
            AttendanceLog.employee_id == emp.id,
            AttendanceLog.ts >= start_dt,
            AttendanceLog.ts < next_month_dt,
        )
        .order_by(AttendanceLog.ts.asc())
        .all()
    )

    # Group by day -> take earliest record per day
    first_log_per_day: Dict[date, AttendanceLog] = {}
    for l in logs:
        d = l.ts.date()
        if d not in first_log_per_day:
            first_log_per_day[d] = l  # earliest because logs sorted asc

    present_days = len(first_log_per_day)
    late_days = sum(1 for l in first_log_per_day.values() if l.lateness_minutes > 0)
    total_late_minutes = sum(l.lateness_minutes for l in first_log_per_day.values())

    working_days = _business_days_in_month(y, m)
    absent_days = max(0, working_days - present_days)

    month_name = calendar.month_name[m]
    summary_text = (
        f"{emp.full_name} in {month_name} {y}: "
        f"{present_days} days present, {late_days} days late, {absent_days} days absent."
    )
    if speak:
        say(summary_text)

    return {
        "ok": True,
        "employee": {"id": emp.id, "emp_code": emp.emp_code, "full_name": emp.full_name},
        "year": y,
        "month": m,
        "month_name": month_name,
        "present_days": present_days,
        "late_days": late_days,
        "absent_days": absent_days,
        "working_days": working_days,
        "total_late_minutes": total_late_minutes,
        "summary_text": summary_text,
    }
