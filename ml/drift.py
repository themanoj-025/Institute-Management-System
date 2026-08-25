"""
Feature-distribution drift detection for ML model monitoring.

Uses the Population Stability Index (PSI) to compare current production
feature distributions against reference distributions saved at training time.

A PSI > 0.1 (configurable) is flagged as drift. The result is stored in
SystemConfig so admin dashboards can display "model may be stale, drift
detected" warnings.

Supports:
- Continuous features via PSI with configurable binning strategies
- Categorical features via a proportion-shift metric (CPSI)
- Wasserstein distance as an additional distributional metric
- Binning strategies: decile, Sturges' rule, Freedman-Diaconis rule, uniform

Usage::

    from ml.drift import compute_drift_report

    session = SessionLocal()
    report = compute_drift_report(session)
    # report = {"drift_detected": bool, "feature_scores": {...}, "max_psi": float}
"""

import json
import logging
from enum import Enum
from math import ceil, log2
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ml.features import FEATURE_NAMES, compute_all_features

logger = logging.getLogger("ml.drift")

# Paths

MODELS_DIR = Path(__file__).resolve().parent / "models"
REFERENCE_FILE = MODELS_DIR / "reference_distributions.json"

# Default thresholds

DEFAULT_PSI_THRESHOLD = 0.10  # PSI > 0.1 = moderate drift
DEFAULT_HIGH_PSI_THRESHOLD = 0.25  # PSI > 0.25 = severe drift
DEFAULT_WASSERSTEIN_THRESHOLD = 0.5  # Wasserstein distance threshold

# Categorical features (binary/boolean flags and course_id)

CATEGORICAL_FEATURES = {"gender_male", "course_id", "fee_overdue_count"}

# Binning strategies


class BinningStrategy(str, Enum):
    DECILE = "decile"  # 10 equal-frequency bins (default)
    STURGES = "sturges"  # Sturges' rule: 1 + log2(n)
    FREEDMAN_DIACONIS = "fd"  # Freedman-Diaconis rule: 2 * IQR * n^(-1/3)
    UNIFORM = "uniform"  # Equal-width bins


def _estimate_n_bins_sturges(n_samples: int) -> int:
    """Sturges' rule: k = ceil(1 + log2(n))."""
    return max(2, ceil(1 + log2(max(n_samples, 2))))


def _estimate_n_bins_fd(n_samples: int, values: np.ndarray) -> int:
    """Freedman-Diaconis rule: bin_width = 2 * IQR * n^(-1/3)."""
    if n_samples < 2:
        return 10
    iqr = float(np.percentile(values, 75) - np.percentile(values, 25))
    if iqr == 0:
        return 10
    bin_width = 2.0 * iqr * (n_samples ** (-1.0 / 3.0))
    if bin_width <= 0:
        return 10
    data_range = float(np.max(values) - np.min(values))
    return max(2, min(50, int(ceil(data_range / bin_width))))


def _get_n_bins(
    n_samples: int,
    values: np.ndarray,
    strategy: BinningStrategy,
) -> int:
    """Determine number of bins based on the selected strategy."""
    if strategy == BinningStrategy.STURGES:
        return _estimate_n_bins_sturges(n_samples)
    elif strategy == BinningStrategy.FREEDMAN_DIACONIS:
        return _estimate_n_bins_fd(n_samples, values)
    elif strategy == BinningStrategy.UNIFORM:
        # Default to 20 equal-width bins for uniform strategy
        return min(20, max(2, n_samples // 10))
    else:  # DECILE (default)
        return 10


# PSI computation for continuous features


def _compute_feature_psi(
    reference: np.ndarray,
    current: np.ndarray,
    min_bins: int = 10,
    eps: float = 1e-6,
    binning_strategy: BinningStrategy = BinningStrategy.DECILE,
) -> float:
    """Compute the Population Stability Index for a single continuous feature.

    PSI measures how much a feature's distribution has shifted:

        PSI = sum((P_i - Q_i) * ln(P_i / Q_i))

    Where P_i is the proportion in bin *i* for the reference distribution
    and Q_i is the proportion in the same bin for the current distribution.

    Parameters
    ----------
    reference : np.ndarray
        Feature values from the training/validation set (reference).
    current : np.ndarray
        Feature values from the production period (current).
    min_bins : int
        Minimum number of bins to use (overridden by strategy if higher).
    eps : float
        Small epsilon to avoid division-by-zero or log(0).
    binning_strategy : BinningStrategy
        Strategy for determining bin count and placement.

    Returns
    -------
    float
        PSI value for this feature.
    """
    if len(reference) == 0 or len(current) == 0:
        return 0.0

    all_values = np.concatenate([reference, current])
    if np.all(all_values == all_values[0]):
        return 0.0

    # Determine actual bin count based on strategy
    actual_bins = _get_n_bins(len(reference), reference, binning_strategy)
    actual_bins = max(actual_bins, min_bins)  # Ensure at least min_bins

    # Create bins using percentiles of the reference distribution
    percentiles = np.linspace(0, 100, actual_bins + 1)[1:-1]  # exclude 0 and 100
    bin_edges = np.percentile(reference, percentiles)
    bin_edges = np.unique(bin_edges)  # Deduplicate for constant segments

    if len(bin_edges) < 2:
        return 0.0

    # Bin both distributions
    ref_binned = np.digitize(reference, bin_edges)
    cur_binned = np.digitize(current, bin_edges)
    n_bins_actual = len(bin_edges) + 1

    psi = 0.0
    for bin_idx in range(n_bins_actual):
        p = np.sum(ref_binned == bin_idx) / len(reference)
        q = np.sum(cur_binned == bin_idx) / len(current)

        p = np.clip(p, eps, 1.0)
        q = np.clip(q, eps, 1.0)

        psi += (p - q) * np.log(p / q)

    return float(psi)


# Categorical PSI (CPSI) — proportion-shift metric


def _compute_categorical_psi(
    reference: np.ndarray,
    current: np.ndarray,
    eps: float = 1e-6,
) -> float:
    """Compute a proportion-shift metric for categorical features.

    Compares the proportion of unique values (categories) between reference
    and current distributions using the same PSI formula but treating each
    unique value as its own bin.

    For binary features (e.g., gender_male), this measures the shift in
    the proportion of 1s vs 0s. For multi-category features (e.g., course_id),
    it measures the shift across all categories.

    Returns
    -------
    float
        CPSI value. > 0.10 indicates significant category proportion shift.
    """
    if len(reference) == 0 or len(current) == 0:
        return 0.0

    # Get all unique categories across both distributions
    all_categories = np.unique(np.concatenate([reference, current]))

    cpsi = 0.0
    for cat in all_categories:
        p = np.sum(reference == cat) / len(reference)
        q = np.sum(current == cat) / len(current)

        p = np.clip(p, eps, 1.0)
        q = np.clip(q, eps, 1.0)

        cpsi += (p - q) * np.log(p / q)

    return float(cpsi)


# Wasserstein distance


def _compute_wasserstein_distance(
    reference: np.ndarray,
    current: np.ndarray,
) -> float:
    """Compute the Wasserstein (Earth Mover's) distance between two distributions.

    This provides a complementary metric to PSI that measures the minimum
    "work" required to transform one distribution into another. It is more
    sensitive to shifts in the body of the distribution than PSI.

    For 1D distributions, this is simply the L1 distance between the
    empirical CDFs: W_1 = integral(|CDF_ref - CDF_cur|).

    Returns
    -------
    float
        Wasserstein distance. Higher values indicate more distributional shift.
    """
    if len(reference) == 0 or len(current) == 0:
        return 0.0

    # Sort both arrays and compute the L1 distance between sorted values
    ref_sorted = np.sort(reference)
    cur_sorted = np.sort(current)

    # Interpolate the smaller array to match the larger one's length
    n_ref = len(ref_sorted)
    n_cur = len(cur_sorted)

    if n_ref < n_cur:
        # Upsample reference to match current
        ref_interp = np.interp(
            np.linspace(0, n_ref - 1, n_cur),
            np.arange(n_ref),
            ref_sorted,
        )
        return float(np.mean(np.abs(ref_interp - cur_sorted)))
    elif n_cur < n_ref:
        cur_interp = np.interp(
            np.linspace(0, n_cur - 1, n_ref),
            np.arange(n_cur),
            cur_sorted,
        )
        return float(np.mean(np.abs(ref_sorted - cur_interp)))
    else:
        return float(np.mean(np.abs(ref_sorted - cur_sorted)))


# Saved reference distributions


def _is_feature_categorical(col_name: str, values: np.ndarray) -> bool:
    """Heuristic to determine if a feature is categorical.

    A feature is considered categorical if:
    1. It's in the CATEGORICAL_FEATURES set, OR
    2. It has fewer than 10 unique values and they are integer-like
    """
    if col_name in CATEGORICAL_FEATURES:
        return True
    unique_count = len(np.unique(values))
    if unique_count < 10 and np.all(values == values.astype(int)):
        return True
    return False


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
    except Exception as e:
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
            "n": int(len(current_values)),
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
