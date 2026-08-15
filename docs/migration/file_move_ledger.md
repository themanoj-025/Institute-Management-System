# BB-IMS — File Move Ledger

## This pass (2026-08-11)

| Old path | New path | Category | Reason | Risk | Verified |
|---|---|---|---|---|---|
| `docs/migration_summary.md` | `docs/migration/migration_summary.md` | Meta/docs | Consolidate migration records under `docs/migration/` per enterprise standard | Low (docs only) | ✅ `git mv` preserved history; no inbound refs found |

## Prior pass (v5.0 modernization, commit `569812d`)

The v5.0 pass moved application code into the current layout. Its complete
file-move log is preserved at `docs/migration/migration_summary.md`
(§ File move log, § Import/reference update summary, § Verification report).

## Non-moves (documented decisions)

| Path | Decision | Reason |
|---|---|---|
| `api/**`, `services/**`, `modules/**`, `database/**`, `auth/**`, `ml/**`, `analytics/**`, `notifications/**`, `ui/**`, `landing/**`, `utils/**`, `config/**` | keep | Canonical backend layering; Docker/CI/Makefile entry contract |
| `web/**` | keep | React/Vite build contract (package.json, vitest) |
| `main.py`, `celery_app.py` (root) | keep | Streamlit + Celery entry points referenced by Docker/scripts |
| `ml/models/risk_v1_candidate_*.json` (on disk) | leave (untracked) | HPO experiment candidates — already gitignored (`ml/models/*.json` + negations); only promoted model + manifests tracked |
| `.gemini/`, `web/node_modules/`, `web/coverage/`, `logs/`, `coverage.xml`, `database/bb_ims.db`, `.env` | leave (untracked) | Local tooling/runtime/build artifacts, correctly gitignored |
