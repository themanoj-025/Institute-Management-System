<p align="center">
  <img src="https://img.shields.io/badge/BB--IMS-Institute%20Management%20System-blue?style=for-the-badge" alt="BB-IMS Logo" />
</p>

<h1 align="center">Binary Brain Institute Management System (BB-IMS)</h1>

<p align="center">
  <strong>Comprehensive educational institute management platform: unified operations across CustomTkinter desktop, React web SPA, and FastAPI REST backend.</strong>
</p>

<p align="center">
  <a href="https://github.com/themanoj-025/Institute-Management-System/actions"><img src="https://img.shields.io/github/actions/workflow/status/themanoj-025/Institute-Management-System/ci.yml?style=flat-square&label=CI" alt="CI Status" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License MIT" /></a>
  <a href="https://github.com/themanoj-025/Institute-Management-System/stargazers"><img src="https://img.shields.io/github/stars/themanoj-025/Institute-Management-System?style=social" alt="GitHub Stars" /></a>
  <a href="https://github.com/themanoj-025/Institute-Management-System/issues"><img src="https://img.shields.io/github/issues/themanoj-025/Institute-Management-System?style=flat-square" alt="GitHub Issues" /></a>
  <a href="https://github.com/themanoj-025/Institute-Management-System/pulls"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square" alt="PRs Welcome" /></a>
</p>

---

## Overview

Binary Brain Institute Management System (BB-IMS) streamlines administrative, academic, and financial workflows for schools, coaching institutes, and training centers. Designed around a single shared domain service layer, it supports desktop offline operation (via CustomTkinter), browser-based administration (via a React 19 SPA), and programmatic integration (via FastAPI).

It manages the complete educational lifecycle including student admissions, faculty assignments, session timetables, attendance tracking, fee invoicing, and ML-assisted student risk analytics.

---

## Table of Contents

- [Supported Interfaces](#supported-interfaces)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Security](#security)
- [Testing](#testing)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)

---

## Supported Interfaces

| Interface | Technology | Target Users |
| :--- | :--- | :--- |
| **Desktop Client** | Python 3.10+, CustomTkinter | Administrators and front-desk staff (offline-first capable) |
| **Web Dashboard** | React 19 + Vite SPA | Remote administrators, instructors, and staff |
| **REST API** | FastAPI /v1/ (50+ endpoints) | Backend services, mobile apps, and third-party integrations |

All interfaces interact with the same underlying service modules in `services/` and database models in `database/`, eliminating duplicated business rules.

---

## Tech Stack

| Domain | Technologies |
| :--- | :--- |
| **Desktop Application** | Python, CustomTkinter, Matplotlib |
| **Web Frontend** | React 19, TypeScript, Tailwind CSS, Vite |
| **Backend REST API** | FastAPI, Pydantic v2, Uvicorn |
| **Database & ORM** | PostgreSQL 16 / SQLite, SQLAlchemy 2.x, Alembic |
| **Task Queue & Workers**| Celery, Redis |
| **Authentication** | JWT (RS256 / HS256), bcrypt password hashing |

---

## Architecture

```text
  ┌───────────────────────┐             ┌───────────────────────┐
  │ CustomTkinter Desktop │             │   React 19 Vite SPA   │
  │     (ui/ / main.py)   │             │        (web/)         │
  └───────────┬───────────┘             └───────────┬───────────┘
              │                                     │
              │  Direct ORM / API                  │ HTTP REST API
              └──────────────────┐ ┌────────────────┘
                                 ▼ ▼
                      ┌───────────────────────┐
                      │    FastAPI Server     │
                      │     (api/main.py)     │
                      └──────────┬────────────┘
                                 │
                      ┌──────────┴────────────┐
                      │ Shared Services Layer │
                      │  (services/, auth/)   │
                      └──────────┬────────────┘
                                 │
                      ┌──────────┴────────────┐
                      │ SQLAlchemy 2.x / DB   │
                      │ (PostgreSQL / SQLite) │
                      └───────────────────────┘
```

---

## Project Structure

```text
Institute-Management-System/
├── api/                    # FastAPI routes, schemas, rate limiter, and dependencies
├── auth/                   # Authentication, JWT handling, and password hashing
├── database/               # SQLAlchemy models and database session management
├── services/               # Shared domain business logic (students, fees, attendance)
├── ui/                     # CustomTkinter desktop interface views and controllers
├── web/                    # React 19 web single-page application
├── ml/                     # Student risk analytics and performance ML models
├── tests/                  # Pytest backend test suite
├── alembic.ini             # Alembic database migration configuration
├── celery_app.py           # Celery asynchronous task configuration
├── docker-compose.yml      # Multi-container orchestration (API, Web, DB, Redis)
├── main.py                 # Desktop application entry point
├── pyproject.toml          # Python build and linting configuration
├── requirements.txt        # Backend dependencies
└── README.md               # Project documentation
```

---

## Prerequisites

- **Python**: `>= 3.10`
- **Node.js**: `>= 18.0` (required for web frontend development)
- **Database**: PostgreSQL 16 (or local SQLite for dev)

---

## Quick Start

### 1. Backend & Database Setup

```bash
# Clone the repository
git clone https://github.com/themanoj-025/Institute-Management-System.git
cd Institute-Management-System

# Setup virtual environment
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\Scripts\Activate.ps1

# Install Python dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head
```

### 2. Choose Your Interface

**Option A: Desktop Client**
```bash
python main.py
```

**Option B: FastAPI REST Server**
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```
*Access interactive Swagger documentation at http://localhost:8000/docs.*

**Option C: React Web Dashboard**
```bash
cd web
npm install
npm run dev
```
*Access the React SPA at http://localhost:5173.*

---

## API Reference

The FastAPI service exposes endpoints under `/api/v1/`:

| Module | Typical Routes |
| :--- | :--- |
| **Auth** | `POST /v1/auth/login`, `POST /v1/auth/refresh` |
| **Students** | `GET /v1/students`, `POST /v1/students`, `PATCH /v1/students/{id}` |
| **Faculty & Staff** | `GET /v1/staff`, `POST /v1/staff`, `PATCH /v1/staff/{id}` |
| **Courses & Classes** | `GET /v1/courses`, `GET /v1/subjects`, `POST /v1/sessions` |
| **Attendance** | `GET /v1/attendance`, `POST /v1/attendance` |
| **Fee Management** | `GET /v1/fees`, `POST /v1/fees`, `PATCH /v1/fees/{id}` |
| **Reports** | `GET /v1/reports/attendance`, `GET /v1/reports/fees` |

---

## Configuration

Settings can be specified in `.env` (copy from `.env.example`):

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `DATABASE_URL` | `sqlite:///ims.db` | Development SQLite database path |
| `DATABASE_URL_POSTGRES` | `postgresql://...` | Production PostgreSQL connection string |
| `JWT_SECRET` | `""` | Cryptographic secret for signing tokens |
| `REDIS_URL` | `redis://localhost:6379/0` | Message broker for Celery tasks |
| `LOG_LEVEL` | `info` | Application logging level |

---

## Security

- **Cryptographic Token Verification**: Implements JWT authentication with token rotation.
- **Role-Based Access Control**: Strict segregation between Admin, Staff, and Student permissions.
- **Input Sanitization**: Pydantic v2 schemas validate all payload structures before execution.
- Review [SECURITY.md](SECURITY.md) for vulnerability disclosure procedures.

---

## Testing

```bash
# Run backend test suite
pytest tests/ -v
```

---

## Roadmap

- [x] CustomTkinter desktop interface
- [x] React 19 web dashboard
- [x] Comprehensive FastAPI backend
- [x] Concurrency-safe financial transactions
- [ ] Multi-tenant organization support <!-- TODO: Track in GitHub issue -->
- [ ] Biometric hardware integration for attendance <!-- TODO: Track in GitHub issue -->

---

## Contributing

Contributions are welcomed! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Support

- 🐛 **Issue Tracker**: [GitHub Issues](https://github.com/themanoj-025/Institute-Management-System/issues)
- 💬 **Discussions & Feedback**: [GitHub Pull Requests](https://github.com/themanoj-025/Institute-Management-System/pulls)
