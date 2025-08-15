# F:\PythonProject\face-attendance\app\db\models.py

from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey
from datetime import datetime
from app.db.base import Base

# ---------- Employee ----------
class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    emp_code = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=False)

    # Optional extra fields (keep or remove as you like)
    department = Column(String, nullable=True)
    designation = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    joining_date = Column(Date, nullable=True)
    notes = Column(String, nullable=True)

    photo_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# ---------- Shift ----------
class Shift(Base):
    __tablename__ = "shifts"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)              # e.g., "Morning"
    start_hhmm = Column(String, nullable=False, default="09:00")    # "HH:MM"
    end_hhmm = Column(String, nullable=False, default="17:00")
    grace_minutes = Column(Integer, nullable=False, default=5)

# ---------- AttendanceLog ----------
class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    ts = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String, default="present")  # present
    lateness_minutes = Column(Integer, default=0)
    snapshot_path = Column(String, nullable=True)
