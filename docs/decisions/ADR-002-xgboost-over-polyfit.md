# ADR-002: XGBoost over numpy.polyfit for At-Risk Prediction

**Status**: Accepted
**Date**: 2026-07-24 (updated 2026-07-25)
**Author**: Architecture Team

## Context

The original ML system used `numpy.polyfit` — a simple linear/quadratic regression — to identify at-risk students. This approach:
- Can only model one input feature at a time (e.g., attendance alone or marks alone)
- Cannot capture non-linear interactions between features (e.g., low attendance + declining marks > sum of parts)
- Produces no probability estimate, just a raw fit value
- Has no mechanism for explaining *why* a student was flagged
- Lacks any train/test split or cross-validation infrastructure

## Decision

Use **XGBoost** (gradient-boosted decision trees) for the at-risk classification model, with **SHAP** (SHapley Additive exPlanations) for per-prediction explainability.

## Rationale

### Why XGBoost over simpler alternatives

| Factor | XGBoost | numpy.polyfit | Logistic Regression |
| -------- | --------- | --------------- | ------------------- |
| **Feature interactions** | Automatic (tree splits) | Manual (polynomial features) | Manual (interaction terms) |
| **Non-linearity** | Inherent | Limited (degree of polynomial) | Via feature engineering |
| **Categorical features** | Native handling | One-hot required | One-hot required |
| **Missing values** | Learned split direction | Must impute | Must impute |
| **Regularization** | Built-in (L1/L2) | None | L1/L2 |
| **Explainability** | SHAP, feature importance | Coefficients (if linear) | Coefficients |
| **Calibrated probabilities** | Yes (logistic output) | No | Yes |

### Why SHAP for explainability

- **Consistent**: SHAP values sum to the prediction — teachers can see exactly how each factor contributed
- **Local**: Per-student explanations, not global averages
- **Actionable**: "Attendance dropped 18% in the last 30 days — increases risk by 0.15" is useful for intervention

### Training protocol

- **80/20 stratified train/test split** — preserves class balance
- **5-fold cross-validation** — reduces variance in performance estimates
- **Evaluation**: AUROC, F1, precision, recall — chosen because:
  - AUROC measures ranking quality regardless of threshold
  - F1 balances precision and recall for the minority (at-risk) class
  - Precision/recall are directly interpretable by non-technical stakeholders

## Model Promotion Gate (*Added 2026-07-25*)

The training pipeline includes an automatic promotion gate that compares a
candidate model's primary metric (AUROC) against the currently active model's
AUROC:
- **Promoted**: If `candidate.auroc >= current.auroc`, the model overwrites the
  active `risk_v1` model and becomes the production model
- **Not promoted**: If `candidate.auroc < current.auroc`, the model is saved as
  a versioned candidate (`risk_v1_candidate_YYYYMMDD_HHMMSS`) for inspection
  without affecting the production model

Promotion decisions are persisted to a `promotion_history` database table and
surfaced via `GET /v1/admin/ml/promotion-history` (admin-only, paginated).
Each record includes:
- Candidate model version + metrics (AUROC, F1, precision, recall)
- Active model version + its AUROC at comparison time
- Promotion decision (promoted / not promoted) with reason

## Consequences

- **XGBoost must be installed**: `xgboost` added to requirements
- **SHAP must be installed**: `shap` added to requirements (large dependency)
- **Training cost**: ~1-5 seconds for 1000 students; negligible
- **Model file size**: ~50-200 KB per trained model
- **Feature engineering**: 13 features computed from 5 source tables (attendance, marks, fees, leaves, demographics)
- **Promotion history**: Tracked in DB; visible in admin dashboard and API

## Related

- ADR-005: ML Model Promotion Gate and History API
- `ml/train.py` — Training implementation with promotion gate
- `ml/explain.py` — SHAP explainability
- `ml/evaluate.py` — Evaluation report generation
- `ml/features.py` — Feature engineering pipeline
- `api/main.py` — `GET /v1/admin/ml/promotion-history` endpoint
- ADR-003: Celery for scheduled retraining
