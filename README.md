# Binary Brain Institute Management System (BB-IMS)

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-2563eb?logo=python&logoColor=white)](https://python.org)
[![React 19](https://img.shields.io/badge/React-19-0ea5e9?logo=react&logoColor=white)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-00C7B7?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169e1?logo=postgresql&logoColor=white)](https://postgresql.org)
[![License](https://img.shields.io/badge/License-MIT-10b981)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-348%20passed-22c55e)](https://github.com/CodeWithHardik/Institute-Management-System/actions)

A comprehensive educational institute management platform for small-to-medium coaching institutes, private schools, and training centers. Manages the full institute lifecycle through three interfaces sharing a single business logic layer.

---

## 📋 Table of Contents

- [Interfaces](#interfaces)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Security](#security)
- [ML Pipeline](#ml-pipeline)
- [Project Structure](#project-structure)
- [License](#-license)
- [Contributing](#-contributing)

---

## 📸 Screenshots

> _To add screenshots: run `python main.py` for desktop or `npm run dev` for web, capture your screen, save images to `docs/assets/`, and reference them below._
>
> **Suggested screenshots:**
> - Desktop client dashboard with KPIs
> - React web dashboard (dark mode)
> - Student attendance management
> - Analytics dashboard with SHAP risk cards

---

## Interfaces

| Interface | Stack | Users |
|-----------|-------|-------|
| Desktop Client | CustomTkinter | Admin, Staff, Students (local/offline) |
| Web Dashboard | React 19 + Vite SPA | Admin, Staff (browser-based) |
| REST API | FastAPI /v1/ (50+ endpoints) | All clients, integrations |

---

## Features

### Desktop Client (37 screens)
- **Admin** (17): Dashboard, Students CRUD, Staff CRUD, Courses, Subjects, Sessions, Leave Manager, Fee Management, Notice Board, Timetable Scheduler, Analytics Dashboard, Staff Attendance, Placement Manager, Enquiry Manager, Reports Center, Activity Log Viewer, Settings
- **Staff** (8): Dashboard, Attendance Taker, Result Manager, Student Lookup, My Attendance, Leave, Feedback, Profile
- **Student** (7): Dashboard, Attendance, Results, Fee Status, Leave, Feedback, Profile
- **Shared** (5): Profile, Settings, Leave Apply, Feedback Sender, Notice Viewer

### Web Dashboard (React SPA)
- Dark mode with CSS custom properties
- Command palette (Cmd+K) with fuzzy search
- Dashboard KPIs: student count, fees, collection rate, at-risk count
- Analytics dashboard with Recharts (attendance, fees, course performance)
- Student list with pagination and search
- Staff and course management
- Fees, results, attendance, leave management
- SHAP-powered risk explanation cards
- Toast notifications, loading skeletons, accessibility support

### REST API (50+ endpoints)
- Full CRUD: Students, Staff, Courses, Fees, Placements, Attendance, Results
- JWT authentication with jti (unique token IDs for blacklisting)
- Server-side OTP with SHA-256 hashing
- Rate limiting with sliding-window per endpoint
- Role-based access control with IDOR prevention
- Standardized error responses with ErrorCode enum
- Paginated responses with full metadata

### ML Pipeline
- XGBoost classifier for at-risk student prediction
- 13 engineered features from 5 tables
- SHAP explainability for every prediction
- Automated promotion gate (candidate model must beat current)
- PSI-based drift detection (daily Celery task)

---

## Tech Stack

| Category | Technology |
|----------|-----------|
| Desktop UI | CustomTkinter 5.2.x |
| Web Dashboard | React 19 + Vite 6.x |
| API Framework | FastAPI + Pydantic v2 |
| ORM | SQLAlchemy 2.0.x |
| Database | PostgreSQL 16 / SQLite (WAL mode) |
| Migrations | Alembic (3 revisions) |
| Auth | bcrypt (cost 14) + PyJWT with jti |
| ML | XGBoost + SHAP TreeExplainer |
| Drift Detection | PSI (Population Stability Index) |
| Background Tasks | Celery + Redis |
| Charts | Matplotlib + Seaborn (desktop) / Recharts (web) |
| Reverse Proxy | nginx Alpine |
| Testing | pytest (348+ tests) + Vitest (31+ tests) |
| Code Quality | Black, isort, mypy, ruff, bandit |

---

## Architecture

```
User Interfaces
    ├── Desktop Client (CustomTkinter)
    ├── Web Dashboard (React SPA)
    └── REST API Clients
            │
            ▼
    FastAPI /v1/ (CORS → RateLimiter → Security Headers → Router)
            │
    ┌───────┼──────────────┐
    ▼       ▼              ▼
Service   ML Pipeline   Celery Worker
Layer     (XGBoost)    (email, retrain)
    │       │
    ▼       ▼
SQLAlchemy ORM — PostgreSQL/SQLite
Alembic migrations (3 revisions)
```

---

## Quick Start

### Desktop App (Local/Offline)

```bash
git clone https://github.com/CodeWithHardik/Institute-Management-System.git
cd Institute-Management-System
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py  # Auto-creates SQLite DB + seeds 5000+ demo records
```

### API Server

```bash
pip install -r requirements.txt
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
export ENV=development
uvicorn api.main:app --reload --port 8000
# OpenAPI docs: http://localhost:8000/docs
```

### Web Dashboard

```bash
cd web
npm install
npm run dev
# Opens at http://localhost:5173
```

### Full Stack (Docker Compose)

```bash
echo "SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")" > .env
cd web && npm install && npm run build && cd ..
docker-compose up -d
# http://localhost:80 → Web dashboard
# http://localhost:8000 → API
# http://localhost:8000/docs → OpenAPI docs
```

---

## API Reference

### Authentication
| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/auth/login` | Login (10/min rate limit) |
| POST | `/v1/auth/verify-otp` | Verify OTP (3/10min) |
| POST | `/v1/auth/refresh` | Refresh token |
| POST | `/v1/auth/logout` | Blacklist token |

### Core CRUD
| Resource | Methods | Auth |
|----------|---------|------|
| Students | GET, POST, PUT, PATCH, DELETE | Admin |
| Staff | GET, POST, PUT, PATCH, DELETE | Admin |
| Courses | GET, POST, PUT, PATCH, DELETE | Admin |
| Fees | GET, POST, DELETE (soft) | Admin |
| Attendance | POST bulk | Admin/Staff |
| Results | POST bulk | Admin/Staff |

### Analytics / ML
| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/analytics/at-risk` | At-risk students with SHAP explanations |
| GET | `/v1/analytics/summary` | Full analytics summary |
| PUT | `/v1/admin/config/risk-thresholds` | Update risk thresholds |

---

## Security

| Layer | Measure |
|-------|---------|
| Passwords | bcrypt hashing (cost 14) |
| 2FA | Server-side OTP (SHA-256, 5-min TTL, single-use) |
| Auth | JWT with jti for server-side blacklisting |
| Rate Limiting | Sliding-window per endpoint |
| Account Lockout | After 5 failures, 15-minute lockout |
| Authorization | Role-based + IDOR prevention on every endpoint |
| Headers | 7 security headers (HSTS, CSP, X-Frame-Options) |
| File Upload | MIME validation with magic byte sniffing |

---

## ML Pipeline

### Model: XGBoost Classifier
- **Target**: Binary classification — is this student at risk of dropping out?
- **Features**: 13 features from 5 tables (attendance, marks, fees, leaves, demographics)
- **Training**: 80/20 stratified split, 5-fold CV
- **Evaluation**: AUROC (primary), F1, precision, recall, accuracy

### Promotion Gate
- Candidate model promoted only if AUROC >= current model's AUROC
- Decisions persisted to promotion_history table

### Drift Detection
- Daily Celery task compares current feature distributions against training-time reference using PSI
- PSI > 0.10: flagged as drifted; PSI > 0.25: severe drift

---

## Project Structure

```
├── main.py                         # Desktop app entry point
├── api/main.py                     # FastAPI (50+ endpoints)
├── celery_app.py                   # Celery worker
├── web/                            # React dashboard (Vite SPA)
├── ml/                             # XGBoost + SHAP + Drift pipeline
├── services/                       # 17 shared business logic modules
├── database/                       # SQLAlchemy models, migrations, seeder
├── modules/                        # 35 desktop screen files
├── docs/                           # ADRs, architecture docs
├── tests/                          # 348+ pytest tests
└── scripts/                        # Migration and utility scripts
```

---

## 📄 License

MIT — see [LICENSE](LICENSE).

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing`)
5. Open a Pull Request

---

## ⭐ Show Your Support

- ⭐ Star the repository if you found it useful
- 🐛 [Report a bug](https://github.com/CodeWithHardik/Institute-Management-System/issues)
- 💡 [Request a feature](https://github.com/CodeWithHardik/Institute-Management-System/issues)
---

## ⭐ Star History

[![Last Commit](https://img.shields.io/github/last-commit/themanoj-025/Institute-Management-System?style=flat-square)](https://github.com/themanoj-025/Institute-Management-System)
[![Contributors](https://img.shields.io/github/contributors/themanoj-025/Institute-Management-System?style=flat-square)](https://github.com/themanoj-025/Institute-Management-System/graphs/contributors)

[![Star History Chart](https://api.star-history.com/svg?repos=themanoj-025/Institute-Management-System&type=Date)](https://star-history.com/#Institute-Management-System&Date)
