"""Evaluation metrics and analysis — extracted from evaluate.py."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

logger = logging.getLogger(__name__)

"""
Model evaluation report generator for the ML prediction pipeline.

Generates comprehensive evaluation reports (Markdown + JSON) for trained
models, including classification metrics, confusion matrix, ROC curve data,
feature importance analysis, and per-threshold precision/recall analysis.

Reports are saved alongside the model in the registry directory
(``ml/models/``) for audit and comparison across training runs.

Typical usage::

    from ml.evaluate import load_and_evaluate

    report = load_and_evaluate(session, "risk_v1")
    # report saved as ml/models/risk_v1_eval.md + risk_v1_eval.json
"""

import logging

from ml.features import FEATURE_NAMES, compute_all_features, compute_target
from ml.registry import load_metadata, load_model
from ml.train import DEFAULT_PARAMS
from utils.time import utc_now

logger = logging.getLogger("ml.evaluate")

# Paths

MODELS_DIR = Path(__file__).resolve().parent / "models"


def _eval_markdown_path(name: str) -> Path:
    return MODELS_DIR / f"{name}_eval.md"


def _eval_json_path(name: str) -> Path:
    return MODELS_DIR / f"{name}_eval.json"


# Core evaluation functions


def _classification_metrics_dict(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: np.ndarray,
) -> dict[str, Any]:
    """Compute a comprehensive set of classification metrics.

    Parameters
    ----------
    y_true : np.ndarray
        Ground-truth labels (0 or 1).
    y_pred : np.ndarray
        Predicted labels (0 or 1).
    y_proba : np.ndarray
        Predicted probabilities for the positive class.

    Returns
    -------
    dict
        Keys include accuracy, f1, precision, recall, auroc, and
        per-class metrics.
    """
    metrics: dict[str, Any] = {}

    # Global metrics
    metrics["accuracy"] = round(float(accuracy_score(y_true, y_pred)), 4)
    metrics["f1"] = round(float(f1_score(y_true, y_pred, zero_division=0)), 4)
    metrics["precision"] = round(float(precision_score(y_true, y_pred, zero_division=0)), 4)
    metrics["recall"] = round(float(recall_score(y_true, y_pred, zero_division=0)), 4)

    # AUROC (needs both classes present)
    unique = np.unique(y_true)
    if len(unique) >= 2:
        try:
            metrics["auroc"] = round(float(roc_auc_score(y_true, y_proba)), 4)
        except (ValueError, TypeError):
            metrics["auroc"] = 0.0
    else:
        metrics["auroc"] = 0.0

    # Per-class metrics via sklearn classification_report (structured)
    report_dict = classification_report(y_true, y_pred, output_dict=True, zero_division=0)
    for label in ("0", "1"):
        if label in report_dict:
            metrics[f"class_{label}_precision"] = round(float(report_dict[label]["precision"]), 4)
            metrics[f"class_{label}_recall"] = round(float(report_dict[label]["recall"]), 4)
            metrics[f"class_{label}_f1"] = round(float(report_dict[label]["f1-score"]), 4)
            metrics[f"class_{label}_support"] = int(report_dict[label]["support"])

    # Support
    metrics["total_samples"] = len(y_true)
    metrics["positive_samples"] = int(y_true.sum())
    metrics["negative_samples"] = int(len(y_true) - y_true.sum())

    return metrics


def _confusion_matrix_data(
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> dict[str, Any]:
    """Compute confusion matrix and return as structured data.

    Returns
    -------
    dict with ``matrix`` (2×2 list), ``true_negatives``, ``false_positives``,
    ``false_negatives``, ``true_positives``.
    """
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    return {
        "matrix": [[int(tn), int(fp)], [int(fn), int(tp)]],
        "true_negatives": int(tn),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "true_positives": int(tp),
    }


def _threshold_analysis(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    thresholds: list[float] | None = None,
) -> list[dict[str, Any]]:
    """Compute precision/recall/f1 at multiple decision thresholds.

    Parameters
    ----------
    y_true : np.ndarray
        Ground-truth labels.
    y_proba : np.ndarray
        Predicted probabilities.
    thresholds : list of float, optional
        Thresholds to evaluate. Defaults to
        ``[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]``.

    Returns
    -------
    list of dict
        Each entry: ``threshold``, ``precision``, ``recall``, ``f1``.
    """
    if thresholds is None:
        thresholds = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

    results = []
    for t in thresholds:
        y_pred_t = (y_proba >= t).astype(int)
        results.append(
            {
                "threshold": t,
                "precision": round(float(precision_score(y_true, y_pred_t, zero_division=0)), 4),
                "recall": round(float(recall_score(y_true, y_pred_t, zero_division=0)), 4),
                "f1": round(float(f1_score(y_true, y_pred_t, zero_division=0)), 4),
            }
        )
    return results


def _roc_curve_data(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    max_points: int = 100,
) -> dict[str, Any]:
    """Compute ROC curve points, sampling to *max_points* for charting.

    Returns
    -------
    dict with ``fpr`` (list), ``tpr`` (list), ``thresholds`` (list),
    and ``auroc`` (float).
    """
    fpr, tpr, thresholds = roc_curve(y_true, y_proba)

    # Sample to max_points for manageable chart data
    step = max(1, len(fpr) // max_points)
    sampled_fpr = [round(float(x), 4) for x in fpr[::step]]
    sampled_tpr = [round(float(x), 4) for x in tpr[::step]]
    sampled_thresholds = [round(float(x), 4) for x in thresholds[::step]]

    # Always include the endpoints
    if sampled_fpr[-1] != 1.0:
        sampled_fpr.append(1.0)
        sampled_tpr.append(1.0)
        sampled_thresholds.append(0.0)

    auroc = roc_auc_score(y_true, y_proba)

    return {
        "fpr": sampled_fpr,
        "tpr": sampled_tpr,
        "thresholds": sampled_thresholds,
        "auroc": round(float(auroc), 4),
    }


def _feature_importance_analysis(
    model: Any,
    feature_names: list[str],
    top_n: int = 15,
) -> list[dict[str, Any]]:
    """Extract feature importance from the trained model.

    Supports XGBoost ``feature_importances_`` (``weight``, ``gain``,
    ``cover``) and produces a ranked list.

    Parameters
    ----------
    model : XGBClassifier
    feature_names : list of str
    top_n : int

    Returns
    -------
    list of dict sorted by importance (descending).
    """
    if not hasattr(model, "get_booster"):
        # Fallback: model may be wrapped; try feature_importances_
        if hasattr(model, "feature_importances_"):
            fi = model.feature_importances_
            ranked = sorted(
                [
                    {"feature": name, "importance": round(float(fi[i]), 4)}
                    for i, name in enumerate(feature_names)
                    if i < len(fi)
                ],
                key=lambda x: x["importance"],
                reverse=True,
            )
            return ranked[:top_n]
        return []

    booster = model.get_booster()

    # Get importance by type
    results = {}
    for imp_type in ("weight", "gain", "cover"):
        try:
            score_dict = booster.get_score(importance_type=imp_type)
            total = sum(score_dict.values()) if score_dict else 1.0
            for fname, score in score_dict.items():
                # Map feature name: try direct match first, then f{fid} format
                if fname in feature_names:
                    name = fname
                elif fname.startswith("f") and fname[1:].isdigit():
                    idx = int(fname[1:])
                    name = feature_names[idx] if idx < len(feature_names) else fname
                else:
                    name = fname
                if name not in results:
                    results[name] = {}
                results[name][imp_type] = round(score / total, 4)
        except (RuntimeError, ValueError, OSError) as exc:
            logger.debug("get_score(%s) failed: %s", imp_type, exc)
            continue

    # Build ranked list
    ranked = []
    for name, scores in results.items():
        entry = {"feature": name, **scores}
        # Average importance across types for sorting
        all_scores = [v for v in scores.values() if v is not None]
        entry["importance"] = round(float(np.mean(all_scores)), 4) if all_scores else 0.0
        ranked.append(entry)

    ranked.sort(key=lambda x: x["importance"], reverse=True)
    return ranked[:top_n]


# Report generation


