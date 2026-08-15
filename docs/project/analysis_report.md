# Institute Management System (BBIMS) — Repository Analysis Report (v5.0)

> Generated during the Ultra Master Repository Modernization pass.
> Scope: inventory, classification, duplicate/dead-code audit, and risk assessment.

## 1. Overview

| Attribute | Value |
|---|---|
| **Project** | BBIMS — Institute Management System (Streamlit + FastAPI + React + Celery + ML risk scoring) |
| **Stack** | Python (Streamlit UI, FastAPI API, Celery workers), PostgreSQL + Alembic, Redis, XGBoost risk model, React (Vite) web frontend |
| **Entry points** | `main.py` (Streamlit), `api/main.py` (FastAPI), `celery_app.py` (worker), `web/` (Vite React), `ml/train.py` (ML training) |
| **Package layout** | Feature modules (`modules/`), `services/`, `api/`, `auth/`, `ml/`, `web/` |
| **Tests** | ~36 pytest files + React component tests |

## 2. Entry Points

| Path | Kind | Purpose |
|---|---|---|
| `main.py` | GUI | Streamlit app entry (role-based dashboards) |
| `api/main.py` | ASGI | FastAPI app factory (JWT auth, rate limiting) |
| `celery_app.py` | Worker | Celery task definitions (background jobs) |
| `ml/train.py` | CLI | ML risk-model training |
| `web/` | Web | React (Vite) SPA — `web/src/main.jsx`, pages under `web/src/pages/` |
| `landing/landing_page.py` | GUI | Streamlit landing page |

## 3. Module Inventory

### Feature modules (`modules/`)
| Module | Category | Purpose |
|---|---|---|
| `modules/admin/*` (16 files) | Domain/UI | Admin: dashboard, analytics, fees, courses, sessions, staff, students, subjects, notices, placements, reports, timetable, attendance, leave, enquiry, activity log, feedback |
| `modules/staff/*` (5 files) | Domain/UI | Staff: dashboard, attendance, results, student lookup, my attendance |
| `modules/student/*` (4 files) | Domain/UI | Student: dashboard, fee status, attendance view, results view |
| `modules/shared/*` (4 files) | Domain/UI | Shared: feedback, leave apply, notices, profile, settings |

### Service layer (`services/`)
| Module | Category | Purpose |
|---|---|---|
| `services/*.py` (17 files) | Domain | Business logic: activity, analytics, attendance, auth, course, export, feedback, fee, leave, notice, placement, result, search, staff attendance, staff, student, timetable |

### API layer (`api/`)
| Module | Category | Purpose |
|---|---|---|
| `api/main.py` | API | FastAPI factory |
| `api/rate_limiter.py` | Cross-cutting | Rate limiting |

### Core & cross-cutting
| Module | Category | Purpose |
|---|---|---|
| `auth/role_guard.py`, `auth/session.py` | Cross-cutting | RBAC + session/JWT |
| `config/settings.py`, `config/constants.py`, `config/settings.json` | Configuration | Settings |
| `database/models.py`, `database/db_session.py`, `database/seeder.py`, `database/alembic/` | Data access | ORM + migrations (5 versions) + seed |
| `analytics/engine.py` | Domain | Analytics engine |
| `ml/{train,service,registry,evaluate,explain,drift,features}.py` | Domain | ML risk pipeline |
| `monitoring/alerts.yml` | Infrastructure | Alert config |
| `notifications/{desktop,email}_notifier.py` | Cross-cutting | Notifications |
| `utils/*` (7 files) | Cross-cutting | Logging, time, validators, helpers, observability, config, async_loader |
| `ui/*` (8 files) | Presentation | Streamlit UI components (charts, tables, sidebar, theme, toasts, animations) |
| `landing/` | Presentation | Landing + login dialog |
| `nginx/` | Infrastructure | Reverse proxy config |
| `web/` | Web | React SPA (14 pages, API client, hooks, components, tests) |
| `locales/{en,hi}.json` | Presentation | i18n |

## 4. Duplicate / Dead Code Audit

| Item | Verdict | Evidence |
|---|---|---|
| `AGENTS_FIX.md` (root) | **DELETE** | Leftover "ULTRA MASTER FIX PROMPT v7.0" AI scaffolding, duplicated in 16 sibling repos; only reference is a PROJECT_OVERVIEW tree line (updated) |
| `web/node_modules` | **OK** | Not tracked (0 files) |
| `web/package-lock.json` | **KEEP** | Legit lockfile (canonical for reproducible installs) |
| Runtime DBs | **OK** | `database/*.db*` gitignored; none tracked |
| Caches (`__pycache__/`, `dist/`) | **OK** | Gitignored |

## 5. Security / Quality Findings (flag-only)

- JWT auth + RBAC role guards + rate limiter present; security-hardening tests (`test_security_hardening.py`, `test_idor.py`) pass.
- CI runs coverage with `--fail-under=70` + bandit + pip-audit per workflow docs.
- No hardcoded credentials found in this pass (env-driven via `.env.example`).

## 6. Verification Summary (this pass)

| Check | Result |
|---|---|
| `py_compile` (143 files) | **Clean** (0 errors) |
| `ruff check --select F821,E9,F63,F7,F82` | **Clean** (exit 0) |
| pytest (16 service/security test files) | **200 passed, 0 failed** |
| Test side-effects | ML model JSONs modified by retraining tests were **reverted** (working tree kept clean) |
| Git hygiene | Clean after commit |

## 7. Needs Human Review

1. `ml/train.py` + tests rewrite `ml/models/risk_v1*.json` and `reference_distributions.json` on every run — consider isolating test runs from committed model artifacts (flag only).
