# BB-IMS — Module Dependency Map

## Backend layering

```
config.settings / config.constants   ← imported by every backend module
database.db_session                  ← used by services, seeder, alembic env
database.models                      ← ORM models; used by services
auth.session / auth.role_guard       ← used by api + modules (role-based guards)
utils.*                              ← cross-cutting helpers (logger, time,
                                        validators, helpers, observability, config)

api/main.py          → services.*, auth, config, database, ml.service, analytics
services/*.py (18)   → database.models, auth, utils, ml (service), analytics,
                       notifications (email), config
modules/*            → services.* (feature verticals call the service layer;
                       admin/staff/student/shared never talk to the DB directly)
ml/service.py        → ml/registry.py, ml/models (json artifacts), ml/features,
                       ml/explain, ml/drift
ml/train.py/evaluate.py → ml/features, ml/models (candidates), analytics
analytics/engine.py  → database.models, config
notifications/*      → config, utils (leaf adapters)
landing/*            → services (public pages)
```

## Rules

- **`modules/` is the Streamlit feature layer; `services/` is the shared
  business layer** — both `api` and `modules` delegate to `services`; services
  never import modules or api.
- **`ml/registry.py` is the single model-selection point** — only the
  registry's promoted candidate (`risk_v1.json`) is served; HPO candidates are
  gitignored (`ml/models/*.json` minus tracked manifests).
- **No circular imports** — services import models/utils downward; api/modules
  import services; verified by `tests/audit_imports.py` + CI.
- **Celery boundary** — `celery_app` imports task modules (notifications,
  analytics, ml) but nothing imports celery_app except the worker entry.

## Frontend

```
web/src/main.jsx → App.jsx → components/Layout (sidebar) + pages/*
pages/*          → hooks (useAuth, useApi) + api/client.js
api/client.js    → backend /api/* (JWT)
components/*     → pure UI (Skeleton, RiskCard, Toast, ProtectedRoute, CommandPalette)
```

## External dependencies

FastAPI + uvicorn · SQLAlchemy + Alembic + Postgres/SQLite · Celery + Redis ·
Streamlit (modules/ui/landing) · React + Vite (web/) · scikit-learn/XGBoost
(ml/) · SHAP (ml/explain) · nginx (reverse proxy) · Prometheus/Grafana
(monitoring) · pydantic (settings)
