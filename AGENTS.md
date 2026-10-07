# AGENTS.md — Institute-Management-System

> Canonical project instructions. Pointers like `CLAUDE.md` or
> `.github/copilot-instructions.md` should say "See AGENTS.md".

---

## Project overview

**Institute-Management-System** — a full-stack institute management
platform. Core components:

- **API** — FastAPI CRUD service for institute entities.
- **Admin** — management dashboard for staff, courses, and enrollments.
- **Student / Staff** — entity models and services.
- **Dashboard** — Streamlit app for reporting.

Stack: Python 3.11+ · FastAPI · SQLAlchemy · PostgreSQL · Streamlit.

---

## Exact commands

```bash
# Install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Lint / typecheck / test
make lint
pre-commit run --all-files
python -m mypy . --ignore-missing-imports
python -m pytest tests/ -v --cov=. --cov-fail-under=70

# Run
uvicorn api.main:app --reload
streamlit run dashboard/app.py
```

---

## Folder map

| Path | Purpose |
|------|---------|
| `api/` | FastAPI application (routes, services) |
| `admin/` | Management dashboard |
| `student/` | Student entity + services |
| `staff/` | Staff entity + services |
| `dashboard/` | Streamlit dashboard |
| `tests/` | pytest suite |
| `.github/workflows/` | CI (ruff, mypy, pytest, gitleaks, trivy) |

## Do / don't

- **Do** keep the auth service behind a single interface.
- **Do not** commit `.env` files.
- **Do not** commit PII (personally identifiable information) to the
  repository.

## Security rules

- No secrets in the repository; `gitleaks` CI gate gates on hits.
- PII must be masked or encrypted before any file leaves the sandbox.

## AI-assistance convention

Commits authored by AI must carry the trailer:

```text
AI-Assisted: yes | no | partial
```

See `.gitmessage` for the template. Do not rewrite historic commits
retroactively.
