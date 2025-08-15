# Face Attendance System

A beginner-friendly **Face Recognition Attendance System** built with **FastAPI**, **SQLAlchemy**, and **PyQt**.  
It lets you enroll employees, log attendance using a webcam, and manage data through an admin web interface.

---

## ✨ Features

- **Employee Enrollment** – Add and manage employees.
- **Face Attendance** – Real-time webcam capture & attendance logging.
- **Shift & Lateness Tracking** – Detects late arrivals based on configured shifts.
- **Admin Web Interface** – Manage employees from a browser.
- **REST API** – Flexible integration with other systems.
- **SQLite Database** – Simple and lightweight for quick setup.

---

## 🛠 Tech Stack

- **Backend:** FastAPI, SQLAlchemy
- **Frontend:** Jinja2 Templates (Admin UI), PyQt5 (Kiosk UI)
- **Database:** SQLite (can be swapped to PostgreSQL/MySQL)
- **Other:** OpenCV, Requests

---

## 📦 Installation

### 1️⃣ Clone the Repository
```bash

🚀 Usage

Open Admin UI: Go to http://127.0.0.1:8000/admin/employees to add employees.

Run the kiosk to scan attendance via webcam.

Attendance is stored in the database with timestamps and lateness info.
git clone https://github.com/PJBiswas/face-attendance.git
cd face-attendance
