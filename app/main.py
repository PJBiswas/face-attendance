from fastapi import FastAPI
from app.db.base import Base, engine
from app.api import employees, attendance
from app.admin import routes as admin_routes

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Face Attendance API", version="0.1.0", docs_url="/docs", redoc_url="/redoc")

@app.get("/")
def root(): return {"ok": True, "msg": "API is running"}

@app.get("/test")
def test(): return {"ok": True, "msg": "Test endpoint is working"}

app.include_router(employees.router)
app.include_router(attendance.router)
app.include_router(admin_routes.router)   # admin pages
