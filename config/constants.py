import os
from pathlib import Path

# App Information
APP_NAME = "Binary Brain IMS"
APP_VERSION = "1.0.0"
COMPANY_NAME = "Binary Brain Institute of Technology"

# UI Constants
SIDEBAR_WIDTH_EXPANDED = 220
SIDEBAR_WIDTH_COLLAPSED = 64
ANIMATION_STEPS = 15
ANIMATION_DELAY = 10  # ms

# Roles
ROLE_ADMIN = "admin"
ROLE_STAFF = "staff"
ROLE_STUDENT = "student"
ROLES = [ROLE_ADMIN, ROLE_STAFF, ROLE_STUDENT]

# Status Choices
STATUS_ACTIVE = "active"
STATUS_INACTIVE = "inactive"
STATUS_LOCKED = "locked"

# Leave Statuses
LEAVE_PENDING = "pending"
LEAVE_APPROVED = "approved"
LEAVE_REJECTED = "rejected"

# Fee Statuses
FEE_PAID = "paid"
FEE_PARTIAL = "partial"
FEE_UNPAID = "unpaid"

# Attendance Statuses
ATTENDANCE_PRESENT = "present"
ATTENDANCE_ABSENT = "absent"
ATTENDANCE_LATE = "late"
ATTENDANCE_EXCUSED = "excused"

# Exam Types
EXAM_MIDTERM = "midterm"
EXAM_FINAL = "final"
EXAM_PRACTICAL = "practical"
EXAM_ASSIGNMENT = "assignment"
EXAM_TYPES = [EXAM_MIDTERM, EXAM_FINAL, EXAM_PRACTICAL, EXAM_ASSIGNMENT]

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = os.path.join(BASE_DIR, "database")
UPLOADS_DIR = os.path.join(BASE_DIR, "database", "uploads")

# Courses Data (Matches README)

# Course catalog � see config/courses.py
from config.courses import AVAILABLE_COURSES  # noqa: F401

