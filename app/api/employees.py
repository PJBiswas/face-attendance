# F:\PythonProject\face-attendance\app\api\employees.py

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, date
import os

from app.db.base import get_db
from app.db.models import Employee

router = APIRouter(prefix="/employees", tags=["employees"])

# Where uploaded photos will be saved
EMPLOYEE_IMG_DIR = "employee_photos"
os.makedirs(EMPLOYEE_IMG_DIR, exist_ok=True)


# ----- helpers -----
def _parse_date(s: Optional[str]) -> Optional[date]:
    """Accept multiple formats: YYYY-MM-DD (preferred), DD-MM-YYYY, DD/MM/YYYY, MM/DD/YYYY."""
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise HTTPException(
        status_code=422,
        detail="joining_date must be YYYY-MM-DD or DD-MM-YYYY or DD/MM/YYYY or MM/DD/YYYY",
    )


# ----- create (enroll) -----
@router.post("/enroll")
async def enroll_employee(
    full_name: str = Form(...),
    emp_code: str = Form(...),
    department: Optional[str] = Form(None),
    designation: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    joining_date: Optional[str] = Form(None),  # e.g. 2025-08-14
    notes: Optional[str] = Form(None),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # Ensure unique employee code
    exists = db.query(Employee).filter(Employee.emp_code == emp_code).first()
    if exists:
        raise HTTPException(status_code=409, detail="emp_code already exists")

    # Save uploaded photo
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{emp_code}_{ts}.jpg"
    path = os.path.join(EMPLOYEE_IMG_DIR, filename)
    with open(path, "wb") as f:
        f.write(await photo.read())

    emp = Employee(
        emp_code=emp_code,
        full_name=full_name,
        department=department,
        designation=designation,
        phone=phone,
        email=email,
        joining_date=_parse_date(joining_date),
        notes=notes,
        photo_path=path,
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)

    return {"ok": True, "employee_id": emp.id, "photo_path": path}


# ----- read/list -----
@router.get("")
def list_employees(db: Session = Depends(get_db)):
    return db.query(Employee).order_by(Employee.id.desc()).all()


@router.get("/{emp_id}")
def get_employee(emp_id: int, db: Session = Depends(get_db)):
    emp = db.query(Employee).get(emp_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp


# ----- update -----
@router.put("/{emp_id}")
async def update_employee(
    emp_id: int,
    full_name: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
    designation: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    joining_date: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    emp = db.query(Employee).get(emp_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Patch fields if provided
    if full_name is not None:
        emp.full_name = full_name
    if department is not None:
        emp.department = department
    if designation is not None:
        emp.designation = designation
    if phone is not None:
        emp.phone = phone
    if email is not None:
        emp.email = email
    if joining_date is not None:
        emp.joining_date = _parse_date(joining_date)
    if notes is not None:
        emp.notes = notes

    # Optional new photo upload
    if photo is not None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{emp.emp_code}_{ts}.jpg"
        path = os.path.join(EMPLOYEE_IMG_DIR, filename)
        with open(path, "wb") as f:
            f.write(await photo.read())
        emp.photo_path = path

    db.commit()
    db.refresh(emp)
    return {"ok": True, "employee": emp}


# ----- delete -----
@router.delete("/{emp_id}")
def delete_employee(emp_id: int, db: Session = Depends(get_db)):
    emp = db.query(Employee).get(emp_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    db.delete(emp)
    db.commit()
    return {"ok": True, "deleted_id": emp_id}
