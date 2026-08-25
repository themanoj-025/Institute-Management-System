"""
SHAP-based explainability for ML model predictions.

Provides per-student explanations of why the model flagged a student
as at-risk, surfacing the top contributing features with their values.

The ``explain_prediction()`` function returns human-readable explanations
suitable for display in the admin dashboard's "Why is this student at risk?"
panel.
"""

import logging
from threading import Lock
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger("ml.explain")

# Caching for the SHAP TreeExplainer
# The TreeExplainer is deterministic and expensive to construct.
# We cache it per model version to avoid re-initialisation on every
# prediction call. The cache is invalidated when the active model
# version changes.

_explainer_cache: dict[str, Any] = {}
_explainer_cache_lock = Lock()


def _get_cached_explainer(model, model_version: str | None = None) -> Any | None:
    """Return a cached SHAP TreeExplainer or create and cache one.

    Parameters
    ----------
    model : XGBClassifier
        The trained model to explain.
    model_version : str, optional
        Version identifier for cache invalidation. If ``None``, caching
        is skipped and a fresh explainer is created each call.

    Returns
    -------
    explainer or None
        The ``shap.TreeExplainer`` instance, or ``None`` if SHAP is not
        available.
    """
    if model_version is None:
        # No version info — skip caching
        return _build_explainer(model)

    with _explainer_cache_lock:
        cached = _explainer_cache.get(model_version)
        if cached is not None:
            return cached

        explainer = _build_explainer(model)
        if explainer is not None:
            _explainer_cache[model_version] = explainer
        return explainer


def _build_explainer(model) -> Any | None:
    """Build a SHAP TreeExplainer for the given model."""
    try:
        import shap

        return shap.TreeExplainer(model)
    except Exception as e:
        logger.debug("SHAP TreeExplainer construction failed: %s", e)
        return None


def invalidate_explainer_cache(model_version: str | None = None) -> None:
    """Invalidate the SHAP explainer cache.

    If ``model_version`` is provided, only that version's entry is
    removed. Otherwise, the entire cache is cleared.
    """
    with _explainer_cache_lock:
        if model_version:
            _explainer_cache.pop(model_version, None)
            logger.info("Invalidated SHAP explainer cache for version %s", model_version)
        else:
            _explainer_cache.clear()
            logger.info("Cleared entire SHAP explainer cache")


# Human-readable feature labels

FEATURE_LABELS = {
    "attendance_rate_4wk": "Attendance (last 4 weeks)",
    "attendance_rate_8wk": "Attendance (last 8 weeks)",
    "attendance_rate_overall": "Overall attendance",
    "attendance_trend_slope": "Attendance trend",
    "marks_avg": "Average marks",
    "marks_trend_slope": "Marks trend",
    "marks_completion_rate": "Exam completion rate",
    "leave_count_this_term": "Leave applications",
    "leave_days_total": "Total leave days",
    "fee_payment_ratio": "Fee payment ratio",
    "fee_overdue_count": "Overdue fee installments",
    "gender_male": "Gender (male)",
    "course_id": "Course",
}


def _feature_label(name: str) -> str:
    """Return a human-readable label for a feature name."""
    return FEATURE_LABELS.get(name, name.replace("_", " ").title())


def explain_prediction(
    model: Any,
    features: pd.Series,
    shap_values: np.ndarray | None = None,
    top_n: int = 3,
    threshold: float = 0.01,
    model_version: str | None = None,
) -> list[dict[str, Any]]:
    """Generate a human-readable explanation for a single prediction.

    Uses SHAP values to identify the top-N features that most influenced
    the model's prediction.

    Parameters
    ----------
    model : XGBClassifier
        The trained XGBoost model (must have ``feature_importances_``).
    features : pd.Series
        Feature vector for the student (index = feature names).
    shap_values : np.ndarray, optional
        Pre-computed SHAP values. If ``None`` and SHAP is available, they
        will be computed. If SHAP is not available, uses feature importances
        as a fallback.
    top_n : int
        Number of top contributing features to return (default 3).
    threshold : float
        Minimum absolute SHAP value to include (default 0.01).
    model_version : str, optional
        Model version identifier for SHAP explainer cache invalidation.
        If provided, the TreeExplainer will be cached and reused.

    Returns
    -------
    list[dict]
        Each dict has keys: ``name`` (feature name), ``label`` (human-readable),
        ``value`` (feature value), ``importance`` (SHAP value or feature importance),
        ``direction`` ("increases" or "decreases" risk).
    """
    importances: np.ndarray | None = None

    # Try SHAP first (using cached explainer when model_version is provided)
    if shap_values is not None:
        importances = shap_values
    else:
        try:
            pass

            # Build a small DataFrame for SHAP explainer
            X_df = pd.DataFrame([features.values], columns=features.index)
            # Use cached explainer to avoid re-construction on every call
            explainer = _get_cached_explainer(model, model_version)
            if explainer is None:
                raise RuntimeError("Failed to get SHAP explainer")
            shap_vals = explainer.shap_values(X_df)
            # For binary classification, shap_values shape is (1, n_features)
            importances = shap_vals[0] if shap_vals.ndim > 1 else shap_vals
        except Exception as e:
            logger.debug("SHAP explainer failed, falling back to feature_importances_: %s", e)

    # Fallback: use model's built-in feature importances
    if importances is None:
        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
        else:
            return [
                {
                    "name": "unknown",
                    "label": "No explanation available",
                    "value": 0,
                    "importance": 0,
                    "direction": "neutral",
                }
            ]

    # Build explanation list
    explanations = []
    for i, feat_name in enumerate(features.index):
        if i >= len(importances):
            break
        imp = float(importances[i])
        if abs(imp) < threshold:
            continue

        explanations.append(
            {
                "name": feat_name,
                "label": _feature_label(feat_name),
                "value": float(features.iloc[i]) if i < len(features) else 0.0,
                "importance": round(imp, 4),
                "direction": "increases" if imp > 0 else "decreases",
            }
        )

    # Sort by absolute importance descending, take top_n
    explanations.sort(key=lambda x: abs(x["importance"]), reverse=True)
    return explanations[:top_n]
