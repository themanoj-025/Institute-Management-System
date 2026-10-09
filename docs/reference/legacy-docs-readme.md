# Documentation — Binary Brain Institute Management System

This directory contains architectural decision records (ADRs) and supplementary
documentation for the BB-IMS project.

## Overview

The **Binary Brain Institute Management System (BB-IMS)** is a full-stack
institute management platform with a desktop client (CustomTkinter), a web
dashboard (React 19), and a REST API (FastAPI). It features an ML-driven student
risk prediction pipeline (XGBoost + SHAP), role-based access control, fee
management, attendance tracking, result management, and placement tracking.

**Project status**: All features implemented — desktop GUI (37 screens), REST API (50+ endpoints), web dashboard (15+ pages), ML pipeline (XGBoost + SHAP + drift), analytics dashboards (desktop + web), and full CI/CD pipeline.

## Architecture Decision Records

| ADR | Title | Status | Summary |
| ----- | ------- | -------- | --------- |
| [ADR-001](../decisions/ADR-001-postgresql-production-database.md) | PostgreSQL as Production Database | ✅ Accepted | PostgreSQL for production; SQLite for desktop/offline |
| [ADR-002](../decisions/ADR-002-xgboost-over-polyfit.md) | XGBoost over numpy.polyfit | ✅ Accepted | XGBoost + SHAP for at-risk student prediction |
| [ADR-003](../decisions/ADR-003-celery-for-background-tasks.md) | Celery for Background Tasks | ✅ Accepted | Celery + Redis for async email, ML retraining, cleanup |
| [ADR-004](../decisions/ADR-004-timezone-aware-datetimes.md) | Timezone-Aware Datetimes | ✅ Accepted | `utc_now()` as single source of truth; `DateTime(timezone=True)` |
| [ADR-005](../decisions/ADR-005-ml-model-promotion-gate.md) | ML Model Promotion Gate | ✅ Accepted | Metrics-gated promotion; persisted history via API |
| [ADR-006](../decisions/ADR-006-unified-jwt-auth.md) | Unified JWT Auth for Desktop & Web | ✅ Accepted | Shared auth via `/v1/auth/login`; desktop API integration |

## Key Documents

- **[deployment.md](../technical/Deployment.md)** — Production deployment guide (Docker,
  Let's Encrypt SSL, CI/CD, backup, troubleshooting)
- **`database/`** — SQLAlchemy models, Alembic migrations, seed data
- **`api/main.py`** — FastAPI application with all v1 routes
- **`ml/`** — ML pipeline (training, evaluation, explanation, drift)
- **`services/`** — Service layer business logic

## Deployment

- **Docker**: `docker-compose.yml` (postgres, redis, api, worker, nginx, certbot)
- **Workers**: Celery (`celery_app.py`) with Beat for scheduled tasks
- **CI/CD**: GitHub Actions (lint → test → build → security → deploy)
- **SSL**: Let's Encrypt via certbot (opt-in) or self-signed for local dev
- **Web**: React SPA served by nginx, proxying `/v1/` to FastAPI

## Test Status

| Suite | Tests | Status |
| ------- | ------- | -------- |
| Python backend (pytest) | 348+ | ✅ All passing |
| Web frontend (vitest) | 31+ | ✅ All passing |
| Code coverage | Backend ≥70%, Frontend ≥45% | ✅ Enforced in CI |
