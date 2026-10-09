# BB-IMS — Startup Flow

BB-IMS ships FastAPI (`api/main.py`) + Celery (`celery_app`) + React (`web/`)
+ Streamlit UI (`main.py` → `ui/` + `modules/`). The root Dockerfile runs the
API; `Dockerfile.worker` runs the Celery worker; compose wires postgres, redis,
nginx, monitoring.

## Backend startup (`uvicorn api.main:app`)

1. `api/main.py` imports `config.settings`, `database.db_session`
   (SQLAlchemy engine), `auth.session`, `api.rate_limiter`.
2. Alembic migrations (in `database/alembic/`) applied to Postgres
   (or SQLite dev DB `database/bb_ims.db`).
3. Router registration — the API is the thin layer; business logic lives in
   `services/*` (18 services) which `modules/*` and `api` both consume.
4. `ml/service.py` loads the promoted risk model (`ml/models/risk_v1.json`)
   from the registry (`ml/registry.py`) for predictions/explainability.
5. Ready: `/health`, `/docs`, business endpoints.

## Celery worker (`celery -A celery_app worker`)

1. `celery_app.py` configures the app (Redis broker from env).
2. Consumes queued tasks (notifications via `notifications/email_notifier`,
   analytics refreshes via `analytics/engine.py`, ML jobs).
3. Monitoring via `monitoring/alerts.yml`.

## Streamlit UI (`python main.py` → Streamlit)

1. `main.py` bootstraps the Streamlit multipage app.
2. Feature verticals render from `modules/`:
   - `modules/admin/*` (dashboard, students, staff, fees, courses, …)
   - `modules/staff/*`, `modules/student/*`, `modules/shared/*`
3. Shared widgets from `ui/` (sidebar, data_table, charts, theme, toast,
   global_search, animations, loading_screen).

## Frontend (`web/`, Vite + React)

1. `src/main.jsx` → `App.jsx`; `src/components/Layout` (sidebar shell),
   `ProtectedRoute`, `CommandPalette`, `Toast`.
2. `src/pages/*` (Login, Dashboard, Students, Fees, Results, …) call
   `src/api/client.js` (JWT bearer).
3. `src/hooks/useAuth.jsx` manages session; `useApi.js` wraps fetches.

## Entry points (root)

| Entry | Command |
|---|---|
| API | `uvicorn api.main:app` (Dockerfile CMD) |
| Worker | `celery -A celery_app worker --concurrency=4` (Dockerfile.worker) |
| Streamlit UI | `python main.py` / `streamlit run main.py` |
| Migrate | `alembic upgrade head` (per `database/alembic.ini`) |
| Seed | `python database/seeder.py` |
| Tests | `python -m pytest -v` (Makefile via compose exec) |
| Install | `install.bat` / `install.sh` |
