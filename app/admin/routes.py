from pathlib import Path
from typing import Optional
from datetime import datetime, date

from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import Employee

router = APIRouter(prefix="/admin", tags=["Admin Pages"])

@router.get("/ping")
def admin_ping():
    return {"ok": True, "where": "admin"}


TEMPLATE_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

EMPLOYEE_IMG_DIR = Path("employee_photos")
EMPLOYEE_IMG_DIR.mkdir(parents=True, exist_ok=True)

def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None

@router.get("/employees", response_class=HTMLResponse)
def employees_list(request: Request, db: Session = Depends(get_db)):
    employees = db.query(Employee).order_by(Employee.id.desc()).all()
    return templates.TemplateResponse(
        "employees.html",
        {"request": request, "employees": employees}
    )

@router.post("/employees/new")
async def employees_add(
    emp_code: str = Form(...),
    full_name: str = Form(...),
    department: Optional[str] = Form(None),
    designation: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    joining_date: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    photo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    exists = db.query(Employee).filter(Employee.emp_code == emp_code).first()
    if exists:
        return RedirectResponse(url="/admin/employees?error=exists", status_code=303)

    photo_path = None
    if photo is not None and photo.filename:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{emp_code}_{ts}.jpg"
        disk_path = EMPLOYEE_IMG_DIR / filename
        with open(disk_path, "wb") as f:
            f.write(await photo.read())
        photo_path = str(disk_path)

    emp = Employee(
        emp_code=emp_code,
        full_name=full_name,
        department=department,
        designation=designation,
        email=email,
        joining_date=_parse_date(joining_date),
        notes=notes,
        photo_path=photo_path,
    )
    db.add(emp)
    db.commit()
    return RedirectResponse(url="/admin/employees?ok=1", status_code=303)
