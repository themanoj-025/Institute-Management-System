# BB-IMS — Old Tree → New Tree

## This pass (2026-08-11)

```
Before                                After
──────                                ─────
docs/migration_summary.md      →      docs/migration/migration_summary.md
—                                     docs/module_dependency.md        (new)
—                                     docs/startup_flow.md             (new)
—                                     docs/package_overview.md         (new)
—                                     docs/migration/old_tree_to_new_tree.md (new)
—                                     docs/migration/file_move_ledger.md     (new)
```

## Prior pass (v5.0 modernization, commit `569812d`)

BB-IMS was restructured by the v5.0 pass into the current layout; its record
(scope, changes, file-move log, import updates, verification, risk,
needs-human-review) lives at `docs/migration/migration_summary.md`.
Tree-level view:

```
Before (flat)                         After (canonical)
──────                                ─────
*.py flat modules            →        services/ (business layer) +
                                       modules/ (Streamlit features) +
                                       api/ (FastAPI) + database/ + auth/ +
                                       ml/ + analytics/ + notifications/ +
                                       ui/ + landing/ + utils/ + config/
*.pyx flat React modules     →        web/ (React + Vite SPA)
*.py tests                   →        tests/ (32 modules)
migrations                   →        database/alembic/versions/
models/*.json                →        ml/models/ (candidates gitignored)
nginx/k8s                    →        nginx/ + monitoring/
```

## No-code-move rationale (this pass)

The layout already conforms (service layer + feature modules + interface
packages + web SPA + canonical infra/docs dirs). This pass only consolidates
the migration record and completes the Phase-6 doc suite — zero code changed.
