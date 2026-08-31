"""PSI computation and binning strategies — extracted from drift.py."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

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
from math import ceil, log2
from pathlib import Path

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


