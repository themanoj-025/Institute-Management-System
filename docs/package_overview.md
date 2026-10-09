# BB-IMS — Package & Module Inventory

## Backend packages (root-level Python packages)

| Package | Modules |
|---|---|
| `api/` | `main.py` (FastAPI entry), `rate_limiter.py` |
| `auth/` | `session.py` (JWT/session), `role_guard.py` (RBAC) |
| `services/` | 18 services: `auth_service`, `student_service`, `staff_service`, `course_service`, `fee_service`, `attendance_service`, `staff_attendance_service`, `result_service`, `notice_service`, `leave_service`, `feedback_service`, `placement_service`, `timetable_service`, `activity_service`, `analytics_service`, `search_service`, `export_service` |
| `modules/` | Streamlit feature verticals: `admin/` (18 screens incl. dashboard, manage_students, fee_management, timetable_scheduler, placement_manager), `staff/` (attendance_taker, result_manager, …), `student/` (fee_status, view_attendance, …), `shared/` (profile, leave_apply, …) |
| `database/` | `models.py` (ORM), `db_session.py`, `seeder.py`, `alembic/` (5 migrations) |
| `ml/` | `service.py`, `registry.py`, `train.py`, `evaluate.py`, `explain.py`, `features.py`, `drift.py`, `models/` (promoted risk_v1.json + tracked manifests) |
| `analytics/` | `engine.py` |
| `notifications/` | `email_notifier.py`, `desktop_notifier.py` |
| `ui/` | Streamlit widgets: `sidebar.py`, `components.py`, `data_table.py`, `chart_factory.py`, `theme_manager.py`, `toast.py`, `global_search.py`, `animations.py`, `loading_screen.py` |
| `landing/` | `landing_page.py`, `login_dialog.py` |
| `utils/` | `config.py`, `helpers.py`, `logger.py`, `observability.py`, `time.py`, `validators.py`, `async_loader.py` |
| `config/` | `settings.py`, `constants.py`, `settings.json` |
| `locales/` | `en.json`, `hi.json` (i18n) |
| Root entries | `main.py` (Streamlit), `celery_app.py` (Celery) |

## Frontend: `web/` (React + Vite)

| Area | Modules |
|---|---|
| `src/pages/` | Login, ForgotPassword, ResetPassword, Dashboard, Students, StudentDetail, Staff, Courses, Fees, Attendance, Results, Notices, Leaves, Feedback, Placements, Analytics, Settings |
| `src/components/` | Layout (`Layout`, `Sidebar`), `ProtectedRoute`, `RiskCard`, `Skeleton`, `Toast`, `CommandPalette` |
| `src/hooks/` | `useApi.js`, `useAuth.jsx` |
| `src/api/` | `client.js` (JWT API client) |
| `src/test/` | Vitest suites (`components.test.jsx`, `pages.test.jsx`) |

## Tests: `tests/` (32 modules)

Service tests (`test_*_service.py` ×14), API (`test_api`, `test_api_integration`),
security (`test_security_hardening`, `test_idor`, `test_password_reset`,
`test_token_blacklist_redis`, `test_rate_limits_extended`), ML (`test_ml_service`,
`test_drift`, `test_evaluate`, `test_shap_cache`), integration/e2e
(`test_closeout_integration`, `test_e2e_journey`, `test_ui_flow`),
`audit_imports.py` + `conftest.py`.

## Non-package trees

| Path | Purpose |
|---|---|
| `web/` | React SPA + coverage output (gitignored) |
| `nginx/` | Reverse-proxy config + self-signed certs |
| `monitoring/` | Prometheus alerts |
| `scripts/` | `migrate_sqlite_to_pg.py`, `gen-selfsigned.sh` |
| `docs/` | Full suite (architecture, decisions ADR-001…006, technical/) |
| Root | `install.bat/sh`, `start.bat`, `alembic.ini`, compose + Dockerfiles |
