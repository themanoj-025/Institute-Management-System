# Binary Brain Institute Management System (BB-IMS)

> A comprehensive educational institute management platform with Desktop (CustomTkinter), Web Dashboard (React 19), and REST API (FastAPI) interfaces sharing a single business logic layer.

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-2563eb.svg)](https://python.org)
[![React 19](https://img.shields.io/badge/React-19-0ea5e9.svg)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-00C7B7.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169e1.svg)](https://postgresql.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-10b981.svg)](LICENSE)
[![Tests: 348+](https://img.shields.io/badge/Tests-348%20passed-22c55e.svg)](#testing)

---

## Table of Contents

- [1. Executive Summary](#1-executive-summary)
- [2. Tech Stack & Core Technologies](#2-tech-stack--core-technologies)
- [3. High-Level Architecture](#3-high-level-architecture)
- [4. Complete Folder Structure Tree](#4-complete-folder-structure-tree)
- [5. Exhaustive File-by-File & Folder-by-Folder Breakdown](#5-exhaustive-file-by-file--folder-by-folder-breakdown)
- [6. Data Models & Schemas](#6-data-models--schemas)
- [7. API Surface](#7-api-surface)
- [8. Configuration & Environment Variables](#8-configuration--environment-variables)
- [9. Build, Run & Deployment Instructions](#9-build-run--deployment-instructions)
- [10. Data & Control Flow Walkthroughs](#10-data--control-flow-walkthroughs)
- [11. Dependency Graph Summary](#11-dependency-graph-summary)
- [12. Testing Strategy](#12-testing-strategy)
- [13. Known Issues, Technical Debt & Assumptions](#13-known-issues-technical-debt--assumptions)
- [14. Glossary](#14-glossary)
- [15. Appendix](#15-appendix)

---

## 1. Executive Summary

**BB-IMS** is a comprehensive educational institute management platform designed for small-to-medium coaching institutes, private schools, and training centers. It manages the full institute lifecycle through three interfaces sharing a single business logic layer.

**Target users**: Institute administrators, teaching staff, and students at coaching centers, private schools, and training centers.

**What problem it solves**: Small-to-medium educational institutions need affordable, integrated management tools that handle student records, attendance, fees, courses, staff management, analytics, and ML-powered risk prediction — without expensive enterprise solutions.

**Why it exists**: To provide a complete, open-source institute management system with desktop, web, and API interfaces, plus ML-powered student at-risk prediction.

*Note: The three-interface architecture and ML pipeline details are explicitly documented in the README and source code.*

---

## 2. Tech Stack & Core Technologies

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Language | Python | 3.10+ | Backend, desktop, ML |
| Desktop UI | CustomTkinter | 5.2.x | Desktop client (37 screens) |
| Web Dashboard | React | 19 | SPA frontend |
| Build Tool | Vite | 6.x | Frontend bundling |
| API Framework | FastAPI | 0.115 | REST API (50+ endpoints) |
| ORM | SQLAlchemy | 2.0.x | Database abstraction |
| Database | PostgreSQL | 16 | Production database |
| Database (Dev) | SQLite | WAL mode | Development fallback |
| Migrations | Alembic | 1.13+ | Schema versioning |
| Auth | bcrypt + PyJWT | — | Password hashing + JWT tokens |
| ML | XGBoost | 2.0+ | At-risk student prediction |
| Explainability | SHAP | 0.44+ | Model explanation |
| Drift Detection | PSI | — | Population Stability Index |
| Background Tasks | Celery | 5.4+ | Async email, retrain |
| Cache/Queue | Redis | 5.0+ | Celery broker + caching |
| Charts (Desktop) | Matplotlib + Seaborn | — | Data visualization |
| Charts (Web) | Recharts | — | Web dashboard charts |
| Reverse Proxy | nginx | Alpine | Production serving |
| Testing (Python) | pytest | 9.0+ | 348+ tests |
| Testing (JS) | Vitest | — | 31+ frontend tests |
| Code Quality | Black, isort, mypy, ruff, bandit | — | Linting + formatting |

---

## 3. High-Level Architecture

```
User Interfaces
    ├── Desktop Client (CustomTkinter) — 37 screens
    ├── Web Dashboard (React 19 SPA) — dark mode, command palette
    └── REST API Clients (50+ endpoints)
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

**Architectural Pattern**: **Shared Service Layer** with **Three Interface Frontends**. All three interfaces (Desktop, Web, API) share the same `services/` layer, `database/` models, and `ml/` pipeline. This ensures consistent business logic regardless of the interface used.

---

## 4. Complete Folder Structure Tree

```
Institute-Management-System/
├── .dockerignore
├── .editorconfig
├── .gitattributes
├── .github/
│   ├── CODEOWNERS
│   ├── dependabot.yml
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   └── feature_request.md
│   ├── labeler.yml
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── workflows/
│       └── ci.yml                  # CI pipeline
├── .gitignore
├── .pre-commit-config.yaml
├── .vscode/
│   └── settings.json
├── AGENTS.md
├── alembic.ini
├── analytics/
│   ├── engine.py                   # Analytics computation engine
│   └── __init__.py
├── api/
│   ├── main.py                     # FastAPI application (50+ endpoints)
│   ├── rate_limiter.py             # Sliding-window rate limiting
│   └── __init__.py
├── auth/
│   ├── role_guard.py               # Role-based access control
│   ├── session.py                  # Session tracking
│   └── __init__.py
├── celery_app.py                   # Celery worker configuration
├── config/
│   ├── constants.py                # Application constants
│   ├── settings.json               # Default settings
│   ├── settings.py                 # Configuration management
│   └── __init__.py
├── database/
│   ├── alembic/                    # Database migrations
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/               # 5 migration files
│   ├── alembic.ini
│   ├── db_session.py               # Session management
│   ├── models.py                   # SQLAlchemy models
│   ├── seeder.py                   # Demo data seeder (5000+ records)
│   └── __init__.py
├── docker-compose.yml              # Full stack orchestration
├── Dockerfile                      # API server container
├── Dockerfile.worker               # Celery worker container
├── docs/
│   ├── community/
│   │   └── CONTRIBUTING.md
│   ├── decisions/                  # Architecture Decision Records
│   │   ├── ADR-001-postgresql-production-database.md
│   │   ├── ADR-002-xgboost-over-polyfit.md
│   │   ├── ADR-003-celery-for-background-tasks.md
│   │   ├── ADR-004-timezone-aware-datetimes.md
│   │   ├── ADR-005-ml-model-promotion-gate.md
│   │   └── ADR-006-unified-jwt-auth.md
│   ├── design/
│   │   ├── AppFlow.md
│   │   └── Design.md
│   ├── product/
│   │   └── PRD.md
│   ├── project/
│   │   ├── ImplementationPlan.md
│   │   ├── RiskRegister.md
│   │   ├── Rules.md
│   │   └── Tracker.md
│   ├── reference/
│   │   ├── Glossary.md
│   │   ├── legacy-docs-readme.md
│   │   └── SECURITY_QA_REPORT.md
│   └── technical/
│       ├── alerting.md
│       ├── API.md
│       ├── Deployment.md
│       ├── Schema.md
│       ├── SecurityAndCompliance.md
│       ├── TechSpec.md
│       └── Testing.md
├── install.bat / install.sh        # Platform installers
├── landing/
│   ├── landing_page.py             # Landing page UI
│   ├── login_dialog.py             # Login dialog
│   └── __init__.py
├── LICENSE
├── locales/
│   ├── en.json                     # English translations
│   └── hi.json                     # Hindi translations
├── main.py                         # Desktop app entry point
├── Makefile
├── ml/
│   ├── drift.py                    # PSI-based drift detection
│   ├── evaluate.py                 # Model evaluation
│   ├── explain.py                  # SHAP explanations
│   ├── features.py                 # Feature engineering (13 features)
│   ├── models/                     # Model artifacts
│   │   ├── reference_distributions.json
│   │   └── risk_v1_meta.json
│   ├── registry.py                 # Model registry
│   ├── service.py                  # ML service layer
│   ├── train.py                    # XGBoost training
│   └── __init__.py
├── modules/                        # Desktop screen modules
│   ├── admin/                      # 17 admin screens
│   ├── shared/                     # 5 shared screens
│   ├── staff/                      # 5 staff screens
│   └── student/                    # 4 student screens
├── monitoring/
│   └── alerts.yml                  # Alerting configuration
├── nginx/
│   ├── default.conf                # nginx configuration
│   └── Dockerfile.nginx            # nginx container
├── notifications/
│   ├── desktop_notifier.py         # Desktop notifications
│   ├── email_notifier.py           # Email notifications
│   └── __init__.py
├── PROJECT_ANALYSIS.md
├── PROJECT_OVERVIEW.md             # This file
├── pyproject.toml
├── README.md
├── requirements.txt
├── scripts/
│   ├── gen-selfsigned.sh           # SSL cert generation
│   └── migrate_sqlite_to_pg.py     # SQLite → PostgreSQL migration
├── services/                       # 17 shared business logic modules
│   ├── activity_service.py
│   ├── analytics_service.py
│   ├── attendance_service.py
│   ├── auth_service.py
│   ├── course_service.py
│   ├── export_service.py
│   ├── feedback_service.py
│   ├── fee_service.py
│   ├── leave_service.py
│   ├── notice_service.py
│   ├── placement_service.py
│   ├── result_service.py
│   ├── search_service.py
│   ├── staff_attendance_service.py
│   ├── staff_service.py
│   ├── student_service.py
│   ├── timetable_service.py
│   └── __init__.py
├── start.bat                       # Windows launcher
├── tests/                          # 348+ pytest tests
│   ├── conftest.py
│   ├── test_*.py                   # 30+ test files
│   └── __init__.py
├── ui/                             # Desktop UI components
│   ├── animations.py
│   ├── chart_factory.py
│   ├── components.py
│   ├── data_table.py
│   ├── global_search.py
│   ├── loading_screen.py
│   ├── sidebar.py
│   ├── theme_manager.py
│   ├── toast.py
│   └── __init__.py
├── utils/
│   ├── async_loader.py
│   ├── config.py
│   ├── helpers.py
│   ├── logger.py
│   ├── observability.py
│   ├── time.py
│   ├── validators.py
│   └── __init__.py
└── web/                            # React 19 SPA
    ├── index.html
    ├── package.json
    ├── src/
    │   ├── api/
    │   │   └── client.js
    │   ├── App.css
    │   ├── App.jsx
    │   ├── components/
    │   │   ├── CommandPalette/
    │   │   ├── Layout/
    │   │   ├── ProtectedRoute.jsx
    │   │   ├── RiskCard.jsx
    │   │   ├── Skeleton/
    │   │   └── Toast/
    │   ├── hooks/
    │   │   ├── useApi.js
    │   │   └── useAuth.jsx
    │   ├── main.jsx
    │   ├── pages/                   # 15 React pages
    │   ├── styles/
    │   │   └── variables.css
    │   └── test/
    │       ├── setup.js
    │       └── __tests__/
    └── vite.config.js
```

---

## 5. Exhaustive File-by-File & Folder-by-Folder Breakdown

### Root Entry Points

#### `Institute-Management-System/main.py`
- **Purpose**: Desktop app entry point. Initializes CustomTkinter, creates `BBIMS_App` class with routing, session tracking, global exception handling, and dynamic module loading.
- **Key class**: `BBIMS_App(ctk.CTk)` — Main application window
- **Key methods**: `navigate(route)`, `get_module_class(route)`, `show_landing_page()`, `start_main_app()`

#### `Institute-Management-System/api/main.py`
- **Purpose**: FastAPI application with 50+ endpoints. Handles CORS, rate limiting, security headers, JWT authentication, and route registration.

#### `Institute-Management-System/celery_app.py`
- **Purpose**: Celery worker configuration for background tasks (email notifications, model retraining).

---

### `Institute-Management-System/services/` — Shared Business Logic (17 modules)

All three interfaces share these services:

| Service | Purpose |
|---------|---------|
| `auth_service.py` | Login, registration, OTP, JWT management |
| `student_service.py` | Student CRUD, search, enrollment |
| `staff_service.py` | Staff CRUD, role management |
| `course_service.py` | Course/subject management |
| `attendance_service.py` | Attendance recording and reporting |
| `result_service.py` | Exam results and grading |
| `fee_service.py` | Fee management and tracking |
| `leave_service.py` | Leave applications and approvals |
| `notice_service.py` | Notice board management |
| `feedback_service.py` | Feedback collection |
| `placement_service.py` | Placement tracking |
| `timetable_service.py` | Timetable scheduling |
| `analytics_service.py` | Analytics computation |
| `search_service.py` | Global search across entities |
| `export_service.py` | Data export (CSV, PDF) |
| `activity_service.py` | Activity logging |
| `staff_attendance_service.py` | Staff attendance management |

---

### `Institute-Management-System/ml/` — ML Pipeline

#### `ml/train.py`
- **Purpose**: Trains XGBoost classifier for at-risk student prediction. 13 features from 5 tables, 80/20 stratified split, 5-fold CV.

#### `ml/features.py`
- **Purpose**: Feature engineering — 13 features from attendance, marks, fees, leaves, and demographics tables.

#### `ml/explain.py`
- **Purpose**: SHAP TreeExplainer for per-patient risk explanation.

#### `ml/drift.py`
- **Purpose**: PSI-based daily drift detection via Celery scheduled task.

#### `ml/registry.py`
- **Purpose**: Model versioning and promotion gate (candidate must beat current AUROC).

---

### `Institute-Management-System/database/` — Data Layer

#### `database/models.py`
- **Purpose**: SQLAlchemy ORM models for all entities (students, staff, courses, fees, attendance, results, etc.).

#### `database/seeder.py`
- **Purpose**: Seeds 5000+ demo records for development.

#### `database/alembic/versions/`
- **Purpose**: 5 migration files covering initial schema, system config, OTP codes, soft delete, timezone-aware datetimes, email verification, and password reset tokens.

---

### `Institute-Management-System/web/` — React SPA

- **Framework**: React 19 + Vite 6
- **Styling**: CSS custom properties, dark mode
- **Features**: Command palette (Cmd+K), SHAP risk cards, toast notifications, loading skeletons
- **Pages**: Dashboard, Analytics, Students, Staff, Courses, Fees, Attendance, Results, Leaves, Feedback, Notices, Placements, Settings, Login, ForgotPassword, ResetPassword

---

## 6. Data Models & Schemas

### Core Entities

- **Student**: id, name, email, phone, enrollment_date, course_id, status
- **Staff**: id, name, email, phone, role, department, hire_date
- **Course**: id, name, description, duration, fee
- **Subject**: id, name, course_id, staff_id
- **Attendance**: id, student_id, date, status (present/absent/late)
- **Result**: id, student_id, subject_id, marks, exam_date
- **Fee**: id, student_id, amount, paid_date, status
- **Leave**: id, user_id, start_date, end_date, reason, status
- **Notice**: id, title, content, author_id, created_at
- **Feedback**: id, user_id, rating, comment, created_at
- **Placement**: id, student_id, company, position, package, date

---

## 7. API Surface

### Authentication
| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/auth/login` | Login (10/min rate limit) |
| POST | `/v1/auth/verify-otp` | Verify OTP (3/10min) |
| POST | `/v1/auth/refresh` | Refresh token |
| POST | `/v1/auth/logout` | Blacklist token |

### Core CRUD (Admin-only)
| Resource | Methods |
|----------|---------|
| Students | GET, POST, PUT, PATCH, DELETE |
| Staff | GET, POST, PUT, PATCH, DELETE |
| Courses | GET, POST, PUT, PATCH, DELETE |
| Fees | GET, POST, DELETE (soft) |
| Attendance | POST bulk |
| Results | POST bulk |

### Analytics/ML
| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/analytics/at-risk` | At-risk students with SHAP explanations |
| GET | `/v1/analytics/summary` | Full analytics summary |
| PUT | `/v1/admin/config/risk-thresholds` | Update risk thresholds |

---

## 8. Configuration & Environment Variables

| Variable | Purpose | Default | Required |
|----------|---------|---------|----------|
| `SECRET_KEY` | JWT signing key | — | **Yes** |
| `ENV` | Environment (development/production) | `development` | No |
| `DATABASE_URL` | PostgreSQL connection | SQLite fallback | No (prod: Yes) |
| `REDIS_URL` | Redis connection | `redis://localhost:6379` | No |
| `SMTP_HOST` | Email server | — | No |
| `SMTP_PORT` | Email port | `587` | No |

---

## 9. Build, Run & Deployment Instructions

### Desktop App

```bash
pip install -r requirements.txt
python main.py    # Auto-creates SQLite DB + seeds 5000+ records
```

### API Server

```bash
pip install -r requirements.txt
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
uvicorn api.main:app --reload --port 8000
```

### Web Dashboard

```bash
cd web && npm install && npm run dev
```

### Full Stack (Docker)

```bash
docker-compose up -d
# http://localhost:80 → Web dashboard
# http://localhost:8000 → API
```

---

## 10. Data & Control Flow Walkthroughs

### Flow 1: Student At-Risk Prediction

1. Admin opens Analytics Dashboard
2. System loads student features (13 features from 5 tables)
3. XGBoost model predicts dropout probability
4. SHAP TreeExplainer generates per-feature contributions
5. Risk cards displayed with explanations
6. Drift detection checks feature distributions against reference

---

## 11. Dependency Graph Summary

```
main.py (Desktop) → modules/* → services/* → database/*
api/main.py → services/* → database/*
celery_app.py → services/* → ml/*
ml/* → database/*
web/* → api/main.py (HTTP)
```

---

## 12. Testing Strategy

- **Python**: pytest with 348+ tests covering all services, API endpoints, ML pipeline, security, and UI flow
- **JavaScript**: Vitest with 31+ tests for React components and pages
- **Security**: IDOR prevention, CSRF, rate limiting, password policy, privilege escalation tests

---

## 13. Known Issues, Technical Debt & Assumptions

### Known Issues

1. **Desktop requires display**: CustomTkinter needs a GUI environment.
2. **SQLite limitations**: Dev mode uses SQLite which doesn't support all PostgreSQL features.

### Technical Debt

1. **Dual database support**: Maintaining both SQLite and PostgreSQL schemas adds complexity.
2. **No WebSocket**: Real-time updates not yet implemented.

### Assumptions

1. **Small-to-medium institutes**: Designed for institutions with <10,000 students.
2. **Single-tenant**: Each deployment serves one institute.

---

## 14. Glossary

| Term | Definition |
|------|-----------|
| **BB-IMS** | Binary Brain Institute Management System |
| **PSI** | Population Stability Index — drift detection metric |
| **IDOR** | Insecure Direct Object Reference — security vulnerability |
| **SHAP** | SHapley Additive exPlanations — model explainability |
| **OTP** | One-Time Password — server-side with SHA-256 hashing |
| **jti** | JWT ID — unique token identifier for blacklisting |

---

## 15. Appendix

### Architecture Decision Records

6 ADRs document key decisions: PostgreSQL for production, XGBoost over polyfit, Celery for background tasks, timezone-aware datetimes, ML model promotion gate, and unified JWT auth.

### Desktop Screens (37 total)

- **Admin (17)**: Dashboard, Students, Staff, Courses, Subjects, Sessions, Leave, Feedback, Fee, Notice, Timetable, Analytics, Attendance, Placement, Enquiry, Reports, Activity Logs
- **Staff (5)**: Dashboard, Attendance Taker, Result Manager, Student Lookup, My Attendance
- **Student (4)**: Dashboard, Attendance, Results, Fee Status
- **Shared (5)**: Profile, Settings, Leave Apply, Feedback, Notices

---

*This document was generated as part of a comprehensive project documentation effort. Last updated: August 8, 2026.*
