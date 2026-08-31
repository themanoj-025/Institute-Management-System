"""Data drift detection — extracted from drift.py."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ml.drift_psi import (
    DEFAULT_HIGH_PSI_THRESHOLD,
    DEFAULT_PSI_THRESHOLD,
    DEFAULT_WASSERSTEIN_THRESHOLD,
    BinningStrategy,
    _compute_categorical_psi,
    _compute_feature_psi,
    _compute_wasserstein_distance,
    _get_n_bins,
    _is_feature_categorical,
)

logger = logging.getLogger(__name__)

def _save_reference_distributions(
    X: pd.DataFrame,
    model_name: str,
    metrics: dict[str, Any] | None = None,
) -> str:
    """Save per-feature reference distributions to a JSON file.

    The saved distributions include binned quantile boundaries for PSI
    comparison, summary statistics, and feature type annotations so the
    drift detector can use the correct metric (PSI vs CPSI).

    Parameters
    ----------
    X : pd.DataFrame
        Feature matrix (rows = students, columns = features).
    model_name : str
        Model identifier (e.g. ``risk_v1``).
    metrics : dict, optional
        Training metrics to include alongside distributions.

    Returns
    -------
    str
        Path to the saved reference file.
    """
    reference: dict[str, Any] = {
        "model_name": model_name,
        "feature_order": list(X.columns),
        "n_samples": len(X),
        "features": {},
    }

    if metrics:
        reference["metrics"] = metrics

    for col in X.columns:
        values = X[col].dropna().values
        unique_vals = np.unique(values)

        feature_info: dict[str, Any] = {
            "mean": float(np.mean(values)) if len(values) > 0 else 0.0,
            "std": float(np.std(values)) if len(values) > 0 else 0.0,
            "min": float(np.min(values)) if len(values) > 0 else 0.0,
            "max": float(np.max(values)) if len(values) > 0 else 0.0,
            "percentiles": (
                [float(p) for p in np.percentile(values, range(5, 100, 5))]
                if len(values) > 0
                else []
            ),
            "is_categorical": _is_feature_categorical(col, values),
        }

        # For categorical features, also store category proportions
        if feature_info["is_categorical"] and len(values) > 0:
            cat_counts: dict[str, float] = {}
            for cat_val in unique_vals:
                proportion = float(np.sum(values == cat_val) / len(values))
                cat_counts[str(cat_val)] = round(proportion, 4)
            feature_info["category_proportions"] = cat_counts
            feature_info["unique_categories"] = [str(v) for v in unique_vals]

        reference["features"][col] = feature_info

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    with open(REFERENCE_FILE, "w", encoding="utf-8") as f:
        json.dump(reference, f, indent=2)

    logger.info(
        "Reference distributions saved to %s (%d features)",
        REFERENCE_FILE,
        len(X.columns),
    )
    return str(REFERENCE_FILE)


def load_reference_distributions() -> dict[str, Any] | None:
    """Load the saved reference distributions from disk.

    Returns
    -------
    dict or None
        The reference distributions dict, or ``None`` if no reference
        file exists.
    """
    if not REFERENCE_FILE.exists():
        logger.info("No reference distributions file found at %s", REFERENCE_FILE)
        return None

    try:
        with open(REFERENCE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load reference distributions: %s", e)
        return None


def compute_drift_report(
    session,
    psi_threshold: float = DEFAULT_PSI_THRESHOLD,
    high_psi_threshold: float = DEFAULT_HIGH_PSI_THRESHOLD,
    wasserstein_threshold: float = DEFAULT_WASSERSTEIN_THRESHOLD,
    binning_strategy: BinningStrategy = BinningStrategy.DECILE,
) -> dict[str, Any]:
    """Compare current feature distributions against saved reference.

    Computes PSI (or CPSI for categorical features) for each feature and
    produces a drift report. Also computes Wasserstein distance as a
    complementary metric.

    Parameters
    ----------
    session : sqlalchemy.orm.Session
        Database session for computing current features.
    psi_threshold : float
        PSI/CPSI value above which drift is flagged (default 0.10).
    high_psi_threshold : float
        PSI/CPSI value above which drift is considered severe (default 0.25).
    wasserstein_threshold : float
        Wasserstein distance above which drift is flagged (default 0.5).
    binning_strategy : BinningStrategy
        Strategy for determining bin count (default DECILE).

    Returns
    -------
    dict
        Report with keys:

        - ``drift_detected`` (bool): ``True`` if any feature exceeds
          ``psi_threshold``.
        - ``severe_drift`` (bool): ``True`` if any feature exceeds
          ``high_psi_threshold``.
        - ``feature_count`` (int): Number of features compared.
        - ``features_drifted`` (int): Number of features exceeding threshold.
        - ``max_psi`` (float): Maximum PSI across all features.
        - ``max_psi_feature`` (str): Feature name with highest PSI.
        - ``feature_scores`` (dict): Per-feature drift scores (PSI or CPSI).
        - ``feature_stats`` (dict): Per-feature current distribution stats.
        - ``feature_details`` (dict): Per-feature details including metric type,
          wasserstein distance, and severity.
        - ``n_samples_reference`` (int): Number of samples in reference.
        - ``n_samples_current`` (int): Number of samples in current data.
        - ``error`` (str, optional): Error message if computation failed.
    """
    reference = load_reference_distributions()
    if reference is None:
        return {
            "drift_detected": False,
            "severe_drift": False,
            "feature_count": 0,
            "features_drifted": 0,
            "max_psi": 0.0,
            "max_psi_feature": "",
            "feature_scores": {},
            "feature_stats": {},
            "feature_details": {},
            "n_samples_reference": 0,
            "n_samples_current": 0,
            "error": "No reference distributions found. Train a model first.",
        }

    # Compute current features
    try:
        X_current = compute_all_features(session)
    except (RuntimeError, ValueError, OSError) as e:
        logger.error("Failed to compute current features for drift: %s", e)
        return {
            "drift_detected": False,
            "severe_drift": False,
            "feature_count": 0,
            "features_drifted": 0,
            "max_psi": 0.0,
            "max_psi_feature": "",
            "feature_scores": {},
            "feature_stats": {},
            "feature_details": {},
            "n_samples_reference": reference.get("n_samples", 0),
            "n_samples_current": 0,
            "error": f"Feature computation failed: {e}",
        }

    if X_current.empty:
        return {
            "drift_detected": False,
            "severe_drift": False,
            "feature_count": 0,
            "features_drifted": 0,
            "max_psi": 0.0,
            "max_psi_feature": "",
            "feature_scores": {},
            "feature_stats": {},
            "feature_details": {},
            "n_samples_reference": reference.get("n_samples", 0),
            "n_samples_current": 0,
            "error": "No current feature data available.",
        }

    reference_features = reference.get("features", {})
    feature_order = reference.get("feature_order", FEATURE_NAMES)

    psi_scores: dict[str, float] = {}
    feature_stats: dict[str, dict[str, Any]] = {}
    feature_details: dict[str, dict[str, Any]] = {}
    wasserstein_scores: dict[str, float] = {}
    max_psi = 0.0
    max_psi_feature = ""
    features_drifted = 0

    for col in feature_order:
        if col not in X_current.columns:
            continue

        ref_feature = reference_features.get(col)
        if ref_feature is None:
            continue

        current_values = X_current[col].dropna().values
        if len(current_values) == 0:
            continue

        # Determine if this feature is categorical
        # Check saved annotation first; then check if category_proportions exist (old format);
        # only fall back to heuristic if neither is available
        cat_proportions = ref_feature.get("category_proportions", None)
        is_categorical = ref_feature.get(
            "is_categorical",
            cat_proportions is not None or _is_feature_categorical(col, current_values),
        )

        # Generate a synthetic reference distribution from saved statistics
        rng = np.random.RandomState(42)
        ref_mean = ref_feature.get("mean", 0.0)
        ref_std = max(ref_feature.get("std", 0.0), 1e-6)
        n_ref = reference.get("n_samples", 100)

        if is_categorical:
            # For categorical features: generate reference values from stored category proportions
            cat_proportions = ref_feature.get("category_proportions", {})
            if cat_proportions:
                categories = [float(k) for k in cat_proportions.keys()]
                proportions = list(cat_proportions.values())
                # Normalize proportions to sum to 1
                prop_sum = sum(proportions)
                if prop_sum > 0:
                    proportions = [p / prop_sum for p in proportions]
                reference_values = rng.choice(categories, size=n_ref, p=proportions)
            else:
                reference_values = rng.normal(ref_mean, ref_std, n_ref)
                reference_values = np.clip(
                    reference_values,
                    ref_feature.get("min", 0.0),
                    ref_feature.get("max", 1.0),
                )

            # Use categorical PSI (CPSI) for categorical features
            drift_score = _compute_categorical_psi(reference_values, current_values)
            metric_type = "cpsi"
        else:
            # For continuous features: use normal approximation
            reference_values = rng.normal(ref_mean, ref_std, n_ref)
            reference_values = np.clip(
                reference_values,
                ref_feature.get("min", 0.0),
                ref_feature.get("max", 1.0),
            )

            # Use standard PSI with configurable binning
            drift_score = _compute_feature_psi(
                reference_values,
                current_values,
                binning_strategy=binning_strategy,
            )
            metric_type = "psi"

        # Compute Wasserstein distance for all features
        wass_dist = _compute_wasserstein_distance(reference_values, current_values)
        wasserstein_scores[col] = round(wass_dist, 6)

        psi_scores[col] = round(drift_score, 6)

        # Determine severity
        if drift_score >= high_psi_threshold:
            severity = "severe"
        elif drift_score >= psi_threshold:
            severity = "drifted"
        else:
            severity = "stable"

        # Also flag on Wasserstein distance
        if wass_dist >= wasserstein_threshold and severity == "stable":
            severity = "drifted"

        feature_stats[col] = {
            "mean": round(float(np.mean(current_values)), 4),
            "std": round(float(np.std(current_values)), 4),
            "min": round(float(np.min(current_values)), 4),
            "max": round(float(np.max(current_values)), 4),
            "n": len(current_values),
            "severity": severity,
        }

        feature_details[col] = {
            "metric": metric_type,
            "binning_strategy": binning_strategy.value if not is_categorical else "categorical",
            "score": round(drift_score, 6),
            "wasserstein_distance": round(wass_dist, 6),
            "is_categorical": is_categorical,
            "severity": severity,
            "current_mean": round(float(np.mean(current_values)), 4),
            "reference_mean": ref_mean,
        }

        if drift_score > max_psi:
            max_psi = drift_score
            max_psi_feature = col

        if severity in ("drifted", "severe"):
            features_drifted += 1

    drift_detected = features_drifted > 0
    severe_drift = any(d.get("severity") == "severe" for d in feature_details.values())

    return {
        "drift_detected": drift_detected,
        "severe_drift": severe_drift,
        "feature_count": len(psi_scores),
        "features_drifted": features_drifted,
        "max_psi": round(max_psi, 6),
        "max_psi_feature": max_psi_feature,
        "feature_scores": psi_scores,
        "feature_stats": feature_stats,
        "feature_details": feature_details,
        "wasserstein_scores": wasserstein_scores,
        "n_samples_reference": reference.get("n_samples", 0),
        "n_samples_current": len(X_current),
        "reference_model": reference.get("model_name", ""),
        "binning_strategy_used": binning_strategy.value,
    }
