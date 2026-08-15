# BBIMS — Folder Structure

```
Institute-Management-System/
├── main.py                        # Streamlit app entry
├── celery_app.py                  # Celery worker entry
├── alembic.ini                    # Alembic config
├── pyproject.toml                 # Python manifest
├── requirements.txt               # Python deps
├── Makefile                       # Task runner
├── Dockerfile / Dockerfile.worker # Container builds
├── docker-compose.yml             # Orchestration
├── .pre-commit-config.yaml        # Git hooks
├── .env.example                   # Env-var template
├── install.bat / install.sh / start.bat
│
├── modules/                       # Streamlit feature modules (role-based)
│   ├── admin/                     # 16 admin screens
│   ├── staff/                     # 5 staff screens
│   ├── student/                   # 4 student screens
│   └── shared/                    # 4 shared screens
├── services/                      # 17 domain services (business logic)
├── api/                           # FastAPI (main.py, rate_limiter.py)
├── auth/                          # role_guard.py, session.py (JWT/RBAC)
├── config/                        # settings.py, constants.py, settings.json
├── database/                      # models, db_session, seeder + alembic/ (migrations)
├── ml/                            # train, service, registry, evaluate, explain, drift, features
│   └── models/                    # risk_v1*.json + reference_distributions.json (committed artifacts)
├── analytics/                     # engine.py
├── notifications/                 # email_notifier, desktop_notifier
├── monitoring/                    # alerts.yml
├── landing/                       # landing_page.py, login_dialog.py
├── ui/                            # Streamlit UI kit (charts, tables, sidebar, theme, toast…)
├── utils/                         # logging, time, validators, helpers, observability…
├── locales/                       # en.json, hi.json (i18n)
├── nginx/                         # reverse proxy config
├── web/                           # React SPA (Vite)
│   ├── package.json / vite.config.js
│   └── src/
│       ├── main.jsx               # SPA entry
│       ├── api/client.js          # API client
│       ├── pages/                 # 14 pages
│       ├── components/            # Layout, Sidebar, CommandPalette, ProtectedRoute…
│       ├── hooks/                 # useApi, useAuth
│       ├── styles/                # variables.css
│       └── test/                  # Jest setup + component tests
├── tests/                         # ~36 pytest files (unit, integration, security, e2e)
├── scripts/                       # gen-selfsigned.sh, migrate_sqlite_to_pg.py
├── docs/                          # Full documentation suite (ADRs, design, technical…)
└── README.md, LICENSE, PROJECT_ANALYSIS.md, PROJECT_OVERVIEW.md
```

## Root Hygiene

- Root holds entry points + manifests + config + top-level dirs only.
- `AGENTS_FIX.md` (AI-scaffolding duplicate) **removed** in this pass; stale reference in `PROJECT_OVERVIEW.md` cleaned.
- No tracked runtime DBs, caches, or node_modules.
