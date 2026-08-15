# 🏫 Contributing to Binary Brain Institute Management System

Welcome! This document will help you get set up with the project and understand
our development workflows, conventions, and standards.

**Table of Contents**

- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Development Workflows](#development-workflows)
  - [Desktop App (Local SQLite)](#desktop-app-local-sqlite)
  - [API Server (FastAPI)](#api-server-fastapi)
  - [Web Dashboard (React SPA)](#web-dashboard-react-spa)
  - [Full Stack (Docker Compose)](#full-stack-docker-compose)
- [Coding Conventions](#coding-conventions)
- [Testing](#testing)
  - [Backend Tests](#backend-tests)
  - [Frontend Tests](#frontend-tests)
  - [Running Specific Tests](#running-specific-tests)
- [Pre-commit Hooks](#pre-commit-hooks)
- [Database Migrations](#database-migrations)
- [Pull Request Process](#pull-request-process)
- [Security Guidelines](#security-guidelines)
- [CI/CD Pipeline](#cicd-pipeline)

---

## Prerequisites

| Tool | Version | Purpose |
| ------ | --------- | --------- |
| **Python** | 3.10+ | Backend, API, desktop client |
| **Node.js** | 20+ | Web dashboard (React SPA) |
| **npm** | 10+ | Frontend package management |
| **Docker** | 24+ | Containerized full-stack development |
| **Docker Compose** | 2.x | Multi-service orchestration |
| **Git** | 2.x | Version control |

Optional but recommended:

| Tool | Purpose |
| ------ | --------- |
| **PostgreSQL** 16 | Production database (or use Docker) |
| **Redis** 7 | Celery broker and cache (or use Docker) |

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/CodeWithHardik/Institute-Management-System.git
cd Institute-Management-System
```

### 2. Set up the environment

```bash
# Create a .env file from the example template
cp .env.example .env

# Edit .env and set at least SECRET_KEY (generate one below):
# SECRET_KEY=<your-generated-secret>
```

Generate a secure `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

> ⚠️ **SECRET_KEY is required.** The application will refuse to start if it is
> missing. Pass it via environment variable or add to `.env`.

### 3. Set up Python

```bash
# Create virtual environment
python -m venv venv

# Activate it
# Linux/macOS: source venv/bin/activate
# Windows:    venv\Scripts\activate

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### 4. Set up the Web Dashboard (optional — only needed for frontend work)

```bash
cd web
npm install
cd ..
```

---

## Development Workflows

### Desktop App (Local SQLite)

The simplest way to get started. Runs the full CustomTkinter desktop client with
an auto-created SQLite database that seeds 5000+ demo records on first launch.

```bash
# Activate virtual environment first
python main.py
```

The app will:
1. Create `database/bb_ims.db` (SQLite WAL mode)
2. Run Alembic migrations
3. Seed 5000+ demo records (admin, staff, students, attendance, fees, results)
4. Print login credentials to the terminal

### API Server (FastAPI)

```bash
# Activate virtual environment first
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
export ENV=development

uvicorn api.main:app --reload --port 8000
```

- **OpenAPI docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health check**: http://localhost:8000/health

### Web Dashboard (React SPA)

In a **separate terminal**, run the Vite dev server:

```bash
cd web
npm run dev
```

The dev server runs at **http://localhost:3000** and proxies `/v1/` and `/health`
requests to the API server at `http://localhost:8000`.

To build for production:

```bash
cd web
npm run build   # Output: web/dist/
```

### Full Stack (Docker Compose)

Brings up the entire stack: Postgres + Redis + API + Celery Worker + nginx.

```bash
# 1. Set up .env with production values (see .env.example)
# 2. Build the frontend (it's served by nginx)
cd web && npm install && npm run build && cd ..

# 3. Start all services
docker compose up -d

# Services:
#   http://localhost:80       → Web dashboard (nginx → React SPA)
#   http://localhost:8000     → API (direct, for debugging)
#   http://localhost:8000/docs → OpenAPI docs

# View logs
docker compose logs -f api worker

# Stop everything
docker compose down

# Full teardown (including volumes)
docker compose down -v
```

> **Note for WSL / Windows**: Use `docker compose` (v2) rather than
> `docker-compose` (v1). Ensure the repository is on the WSL filesystem
> for best performance with bind mounts.

---

## Coding Conventions

### Python

We enforce a consistent style with automated tooling:

| Tool | Purpose | Configuration |
| ------ | --------- | --------------- |
| **Black** | Code formatter | Line length 100, `pyproject.toml` |
| **isort** | Import sorting | Black-compatible profile |
| **ruff** | Fast linter | Ignoring E501, F401, E402, E731, E712 |
| **mypy** | Optional static typing | `strict_optional`, `warn_return_any` |
| **bandit** | Security static analysis | Excludes `venv`, `alembic`, `tests` |

Run all checks before pushing:

```bash
# Format code
black --line-length 100 --exclude "venv|alembic" .

# Sort imports
isort --profile black --skip venv --skip alembic --skip web .

# Quick lint
ruff check . --ignore E501,F401,E402,E731,E712 --exclude venv,alembic

# Security scan
bandit -r . -x venv,alembic,tests
```

### Cross-Platform Shell Commands

Many commands in this guide use **bash-style syntax** (`SECRET_KEY=value command`).
If you're on Windows, adapt them as follows:

| Platform | Syntax |
| ---------- | -------- |
| **Linux/macOS (bash/zsh)** | `SECRET_KEY=test-key python -m pytest tests/` |
| **Windows (PowerShell)** | `$env:SECRET_KEY="test-key"; python -m pytest tests/` |
| **Windows (cmd)** | `set SECRET_KEY=test-key && python -m pytest tests/` |

For repeated use, add `SECRET_KEY` to your `.env` file so it's always
automatically loaded.

### Python Code Style Guidelines

- **4-space indentation** (no tabs)
- **Snake case** for functions, variables, and methods
- **PascalCase** for classes
- **Type hints** on all function signatures
- **Docstrings** on public functions, classes, and modules (Google-style)
- **Imports order**: standard library → third-party → local (grouped with blank lines)
- **No wildcard imports** (`from module import *`)
- **No bare `except:`** — always specify exception types
- **Prefer `pathlib.Path`** over `os.path` for new code
- **Use `utc_now()` from `utils/time.py`** instead of `datetime.now(timezone.utc)`

### React / JavaScript

- **ESLint** via Vite's built-in linting
- **Functional components** with hooks (no class components)
- **CSS variables** defined in `web/src/styles/variables.css`
- **Component files** in `web/src/components/` with PascalCase names
- **Page files** in `web/src/pages/` with PascalCase names
- **Custom hooks** in `web/src/hooks/` with `use` prefix

---

## Testing

### Backend Tests

We use **pytest** with `tests/conftest.py` providing shared fixtures:

```bash
# Run all backend tests (348+ tests)
SECRET_KEY=test-key python -m pytest tests/ -v

# Run with coverage (threshold: 70%)
SECRET_KEY=test-key python -m pytest tests/ --cov=services --cov=ml --cov=api --cov-report=term-missing

# Run with verbose output and shorter tracebacks (default)
SECRET_KEY=test-key python -m pytest tests/ -v --tb=short
```

**Important**: `SECRET_KEY` must be set in the environment. Use any non-empty
string for local testing (e.g., `test-key`).

### Frontend Tests

We use **Vitest** with React Testing Library:

```bash
cd web

# Run all frontend tests
npm test

# Run with coverage
npm run test:ci

# Watch mode
npm run test:watch
```

### Running Specific Tests

```bash
# By file
SECRET_KEY=test-key python -m pytest tests/test_auth_service.py -v

# By keyword expression
SECRET_KEY=test-key python -m pytest tests/ -k "otp or token or promotion"

# By marker (if available)
SECRET_KEY=test-key python -m pytest tests/ -m security
```

---

## Pre-commit Hooks

We provide a `.pre-commit-config.yaml` to automate code quality checks before
every commit. These hooks run **black** (formatting), **isort** (import sorting),
and **mypy** (type checking).

```bash
# Install pre-commit
pip install pre-commit

# Install the hooks into your local git repo
pre-commit install
```

After installation, `git commit` will automatically run the configured hooks on
staged files. To skip hooks for a specific commit (use sparingly):

```bash
git commit --no-verify
```

---

## Database Migrations

We use **Alembic** for schema migrations. Migrations are stored in
`database/alembic/versions/`.

```bash
# Navigate to the database directory
cd database

# Apply all pending migrations
SECRET_KEY=test-key python -m alembic -c alembic.ini upgrade head

# Create a new migration (auto-detect changes)
SECRET_KEY=test-key python -m alembic -c alembic.ini revision --autogenerate -m "description"

# Roll back the last migration
SECRET_KEY=test-key python -m alembic -c alembic.ini downgrade -1

# View migration history
SECRET_KEY=test-key python -m alembic -c alembic.ini history

# Check current revision
SECRET_KEY=test-key python -m alembic -c alembic.ini current
```

> Always verify both `upgrade` and `downgrade -1` work on a fresh database
> before committing a new migration.

### Migration Checklist

When adding a new column or table:

1. Update `database/models.py` with the new model/column
2. Generate the migration: `alembic revision --autogenerate`
3. **Review** the generated migration file — autogenerate can miss things
4. Test `upgrade head` on a clean database
5. Test `downgrade -1` to verify reversibility
6. Commit both the model change and the migration file

---

## Pull Request Process

### Before Submitting

Run the full PR checklist:

```bash
# 1. All backend tests pass
SECRET_KEY=test-key python -m pytest tests/ -v --tb=short

# 2. All frontend tests pass (if web files changed)
cd web && npm test

# 3. Code is formatted
black --line-length 100 --exclude "venv|alembic" .
isort --profile black --skip venv --skip alembic --skip web .

# 4. Linter is clean
ruff check . --ignore E501,F401,E402,E731,E712 --exclude venv,alembic

# 5. Security scan passes
bandit -r . -x venv,alembic,tests

# 6. Migrations are up to date
cd database && SECRET_KEY=test-key python -m alembic -c alembic.ini upgrade head

# 7. No datetime.now(timezone.utc) calls outside utils/time.py
grep -rn "datetime\.now(timezone\.utc)" --include="*.py" | grep -v "utils/time.py" || echo "OK"

# 8. Frontend builds (if web files changed)
cd web && npm run build
```

### PR Template

Every PR should include:

- **Description**: What does this change do? Why?
- **Type**: Bug fix, feature, refactor, docs, tests, etc.
- **Testing**: What tests were added or updated?
- **Migration**: Does this require a migration? Has it been tested?
- **API Changes**: List any new/modified endpoints
- **Documentation**: Update README, ADRs, or other docs if needed

### Review Process

1. Ensure CI passes (lint → test → build → security)
2. At least one maintainer review required
3. For migration changes, verify downgrade path works
4. For API changes, verify OpenAPI docs are accurate
5. For ML changes, verify promotion gate tests pass

---

## Security Guidelines

### Authentication

- **`SECRET_KEY`** is required — the app fails to start if missing
- **Passwords** are hashed with bcrypt (cost factor 14), never logged, never returned
- **OTP codes** are SHA-256 hashed server-side, single-use, 5-minute TTL, never in responses
- **JWTs** include unique `jti` for blacklisting; old tokens invalidated on refresh/logout
- **Account lockout** after 5 consecutive failures (15-minute cooldown)

### Data Access

- Every API endpoint uses `require_role()` to enforce role-based access
- Resource-scoped endpoints use `verify_ownership()` to prevent IDOR
- All database access uses SQLAlchemy ORM — **no raw SQL or f-string interpolation**

### Input Validation

- All API request bodies validated via strict Pydantic v2 models
- File uploads validated by MIME content sniffing (not just extension)
- Upload size limited to 5MB server-side
- Rate limiting on login (10/min), OTP (3/10min), refresh (20/min), create (30/min)

### Prohibited Patterns

```
❌ datetime.now(timezone.utc)          — use utc_now() from utils/time.py
❌ Raw f-string SQL                    — use SQLAlchemy ORM
❌ Hardcoded secrets                   — use environment variables
❌ Returning OTP/passwords in API      — SHA-256 hashed, never exposed
❌ Bypassing OTP check                 — login returns otp_required, not JWT
```

### Audit Logging

Authentication events (login success, login failure, OTP verify, logout) are
logged via `services/activity_service.py`. Monitor for:

- Repeated 401/403/429 responses from the same IP
- Account lockout events
- Failed OTP verification attempts
- Blacklisted token usage

---

## CI/CD Pipeline

Our CI/CD pipeline runs on **GitHub Actions** (`.github/workflows/ci.yml`):

| Stage | Tools | When |
| ------- | ------- | ------ |
| **Lint** | ruff + black --check | Every push/PR |
| **Test** | pytest + coverage (≥70%) | After lint |
| **Web Build** | npm ci + npm run build + vitest | After lint |
| **Build** | Docker buildx (API + Worker + Nginx) | After tests |
| **Security** | bandit + pip-audit + gitleaks | After lint |
| **Deploy** | SSH deploy to production | Main branch, manual approval |

### Environment Variables in CI

| Variable | CI Value | Note |
| ---------- | ---------- | ------ |
| `SECRET_KEY` | `test-secret-key-for-ci-12345678` | Non-sensitive test key |
| `DATABASE_URL` | `postgresql://bbims:testpass@localhost:5432/bb_ims_test` | Ephemeral PG service |
| `REDIS_URL` | `redis://localhost:6379/0` | Ephemeral Redis service |
| `ENV` | `test` | Disables production-only features |

---

## Questions?

- Open a [GitHub Issue](https://github.com/CodeWithHardik/Institute-Management-System/issues)
- Check [Architecture Decision Records](../decisions/) for design rationale
- Refer to [README.md](../../README.md) for feature overview and API reference
