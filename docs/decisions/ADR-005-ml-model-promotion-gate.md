# ADR-005: ML Model Promotion Gate with Persisted History

**Status**: Accepted
**Date**: 2026-07-25
**Author**: Architecture Team

## Context

After each training run, the ML pipeline produces a candidate model with
evaluation metrics (accuracy, AUROC, F1, precision, recall). Without a
promotion gate, every training run would overwrite the production model
regardless of quality — a worse model could silently replace a better one.

Additionally, there was no mechanism to:
- View past training runs and their outcomes
- Audit when and why a model was (or wasn't) promoted
- Compare candidate vs. active metrics from previous runs

## Decision

1. **Metrics-gated promotion**: After training, compare the candidate model's
   primary metric (AUROC) against the currently active model's stored AUROC.
   Only promote if `candidate.auroc >= current.auroc`.
2. **Persist decisions**: Store every promotion decision in a
   `promotion_history` database table with full metadata (timestamps, both
   models' metrics, the decision, and the reason).
3. **Expose via API**: `GET /v1/admin/ml/promotion-history` (admin-only,
   paginated) returns structured promotion history.
4. **Expose via UI**: The web dashboard's Settings page shows a promotion
   history table with color-coded PROMOTED/NOT PROMOTED badges.

## Rationale

### Why AUROC as the primary metric

| Metric | Property | Why it's primary |
| -------- | ---------- | ----------------- |
| **AUROC** | Threshold-independent; measures ranking quality | Best single-number metric for comparing models |
| **F1** | Depends on threshold (default 0.5) | Important but threshold-dependent |
| **Precision/Recall** | Trade-off; context-dependent | Used for diagnosis, not gate decisions |

### Why persist to a database table (not log files)

| Option | Pros | Cons |
| -------- | ------ | ------ |
| **Database table** | Queryable, structured, durable | Requires migration |
| **Log files** | No DB change | Not queryable; fragile; lost on rotation |
| **Model metadata file** | Already exists for metrics | No history; single record per model |

### Why a `>=` comparison (not `>`)

Using `>=` (promote if equal or better) prevents churn when models have
identical AUROC. Without this, every retrain would overwrite the active model
with an equivalent one, creating unnecessary file I/O and losing the previous
model's identity.

## Consequences

- **New table**: `promotion_history` created in all environments
- **Alembic migration**: `9a1b2c3d4e5f` creates the table
- **API surface**: New endpoint `GET /v1/admin/ml/promotion-history`
- **Database growth**: ~1 KB per training run; negligible
- **Backward compatibility**: Old models without promotion history are
  handled gracefully (empty list returned)

## Promotion Logic Pseudocode

```python
primary_metric = test_auroc
current_auroc = load_current_model_auroc() or 0.0

if primary_metric >= current_auroc:
    save_as_active_model(model, metrics)
    persist_history(promoted=True, reason=f"AUROC {primary_metric} >= {current_auroc}")
else:
    save_as_candidate(model, metrics, version_suffix)
    persist_history(promoted=False, reason=f"AUROC {primary_metric} < {current_auroc}")
```

## Related

- ADR-002: XGBoost over numpy.polyfit (ML pipeline)
- `ml/train.py` — Promotion gate implementation
- `database/models.py` — `PromotionHistory` model
- `api/main.py` — `GET /v1/admin/ml/promotion-history` endpoint
- `web/src/pages/Settings.jsx` — Web dashboard component
