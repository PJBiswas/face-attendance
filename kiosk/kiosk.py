import sys
import cv2
import requests
from io import BytesIO

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QLineEdit
)
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import QTimer, Qt


API_URL = "http://127.0.0.1:8000"


class Kiosk(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Face Attendance Kiosk")
        self.setStyleSheet("background:#0b1220;color:white;font-size:16px;")
        self.setWindowState(Qt.WindowMaximized)

        # ---- UI widgets ----
        self.video_label = QLabel(alignment=Qt.AlignCenter)
        self.status_label = QLabel("Ready. Please face the camera.", alignment=Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size:24px;margin:12px;")

        self.emp_input = QLineEdit()
        self.emp_input.setPlaceholderText("Enter Employee Code (e.g., Emp001)")
        self.emp_input.setStyleSheet("padding:10px;border-radius:8px;")
        self.emp_input.returnPressed.connect(self.scan_attendance)

        self.btn_test = QPushButton("Test API")
        self.btn_test.setStyleSheet("padding:12px;font-size:18px;background:#1f6feb;border-radius:10px;")
        self.btn_test.clicked.connect(self.test_api)

        self.btn_scan = QPushButton("Scan Attendance")
        self.btn_scan.setStyleSheet("padding:12px;font-size:18px;background:#238636;border-radius:10px;")
        self.btn_scan.clicked.connect(self.scan_attendance)

        # Layout
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Employee Code:"))
        top_row.addWidget(self.emp_input)
        top_row.addWidget(self.btn_scan)

        col = QVBoxLayout()
        col.addWidget(self.video_label, stretch=1)
        col.addLayout(top_row)
        col.addWidget(self.status_label)
        col.addWidget(self.btn_test, alignment=Qt.AlignCenter)
        self.setLayout(col)

        # ---- camera ----
        self.cap = cv2.VideoCapture(0)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    # ---- live preview ----
    def update_frame(self):
        ok, frame = self.cap.read()
        if not ok:
            return
        frame = cv2.flip(frame, 1)  # mirror preview
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qimg))

    # ---- test backend health ----
    def test_api(self):
        try:
            r = requests.get(f"{API_URL}/test", timeout=5)
            if r.status_code == 200:
                msg = r.json().get("msg", "OK")
                self.status_label.setText(f"API says: {msg}")
                self._set_status_ok()
            else:
                self.status_label.setText(f"API error: {r.status_code}")
                self._set_status_err()
        except Exception as e:
            self.status_label.setText(f"Error: {e}")
            self._set_status_err()

    # ---- capture and send check-in ----
    def scan_attendance(self):
        emp_code = self.emp_input.text().strip()
        if not emp_code:
            self.status_label.setText("Please enter Employee Code first.")
            self._set_status_err()
            return

        ok, frame = self.cap.read()
        if not ok:
            self.status_label.setText("Camera error.")
            self._set_status_err()
            return

        # JPEG encode
        ret, jpeg = cv2.imencode(".jpg", frame)
        if not ret:
            self.status_label.setText("Failed to encode snapshot.")
            self._set_status_err()
            return

        files = {"frame": ("frame.jpg", jpeg.tobytes(), "image/jpeg")}
        data = {"emp_code": emp_code}

        try:
            r = requests.post(f"{API_URL}/attendance/checkin", files=files, data=data, timeout=15)
            if r.status_code == 200 and r.json().get("ok"):
                msg = r.json().get("message", "OK")
                self.status_label.setText(msg)
                if "late" in msg.lower():
                    self._set_status_warn()
                else:
                    self._set_status_ok()
            else:
                self.status_label.setText(f"API error: {r.status_code} {r.text}")
                self._set_status_err()
        except Exception as e:
            self.status_label.setText(f"Error: {e}")
            self._set_status_err()

    # ---- status styles ----
    def _set_status_ok(self):
        self.status_label.setStyleSheet("font-size:24px;background:#113f25;color:#a4f4b9;padding:10px;border-radius:10px;")

    def _set_status_warn(self):
        self.status_label.setStyleSheet("font-size:24px;background:#51260e;color:#f2c5b2;padding:10px;border-radius:10px;")

    def _set_status_err(self):
        self.status_label.setStyleSheet("font-size:24px;background:#632020;color:#ffd9d9;padding:10px;border-radius:10px;")

    # ---- graceful close ----
    def closeEvent(self, event):
        if self.cap and self.cap.isOpened():
            self.cap.release()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Kiosk()
    w.show()
    sys.exit(app.exec())
