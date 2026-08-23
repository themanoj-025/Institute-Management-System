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

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

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
        except Exception:
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
    metrics["total_samples"] = int(len(y_true))
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
        except Exception as exc:
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


def _generate_report_data(
    model: Any,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    model_name: str,
    cv_metrics: dict[str, float] | None = None,
    train_samples: int | None = None,
) -> dict[str, Any]:
    """Generate the full evaluation report as a dictionary.

    Parameters
    ----------
    model : XGBClassifier
        Trained model to evaluate.
    X_test : pd.DataFrame
        Test feature matrix.
    y_test : pd.Series
        Test ground-truth labels.
    model_name : str
        Name of the model being evaluated.
    cv_metrics : dict, optional
        Pre-computed cross-validation metrics to include.
    train_samples : int, optional
        Number of training samples used.

    Returns
    -------
    dict
        Complete report data structure.
    """
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    # Convert to numpy for sklearn compatibility
    y_true_np = y_test.values
    y_pred_np = y_pred
    y_proba_np = y_proba

    # Core metrics
    metrics = _classification_metrics_dict(y_true_np, y_pred_np, y_proba_np)

    # Confusion matrix
    confusion = _confusion_matrix_data(y_true_np, y_pred_np)

    # ROC curve data
    roc = _roc_curve_data(y_true_np, y_proba_np)

    # Threshold analysis
    threshold_analysis = _threshold_analysis(y_true_np, y_proba_np)

    # Feature importance
    feature_importance = _feature_importance_analysis(model, list(X_test.columns))

    report: dict[str, Any] = {
        "report_metadata": {
            "model_name": model_name,
            "generated_at": utc_now().isoformat(),
            "test_samples": len(X_test),
            "feature_count": X_test.shape[1],
        },
        "metrics": metrics,
        "confusion_matrix": confusion,
        "roc_curve": roc,
        "threshold_analysis": threshold_analysis,
        "feature_importance": feature_importance,
    }

    if cv_metrics:
        report["cv_metrics"] = cv_metrics

    if train_samples is not None:
        report["report_metadata"]["train_samples"] = train_samples

    return report


def _report_to_markdown(report: dict[str, Any]) -> str:
    """Convert a report dict to a formatted Markdown string."""
    lines: list[str] = []
    meta = report["report_metadata"]
    metrics = report["metrics"]
    confusion = report["confusion_matrix"]
    roc = report["roc_curve"]
    threshold_data = report["threshold_analysis"]
    fi_data = report.get("feature_importance", [])
    cv = report.get("cv_metrics")

    # Header
    lines.append(f"# Model Evaluation Report: `{meta['model_name']}`")
    lines.append("")
    lines.append(f"- **Generated**: {meta['generated_at']}")
    lines.append(f"- **Test samples**: {meta['test_samples']}")
    lines.append(f"- **Feature count**: {meta['feature_count']}")
    if "train_samples" in meta:
        lines.append(f"- **Train samples**: {meta['train_samples']}")
    lines.append("")

    # Classification metrics
    lines.append("## Classification Metrics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    for key in ("accuracy", "precision", "recall", "f1", "auroc"):
        val = metrics.get(key, "—")
        lines.append(f"| {key} | {val} |")
    lines.append("")

    # Per-class metrics
    lines.append("### Per-Class Metrics")
    lines.append("")
    lines.append("| Class | Precision | Recall | F1 | Support |")
    lines.append("|-------|-----------|--------|----|---------|")
    for label in ("0", "1"):
        p = metrics.get(f"class_{label}_precision", "—")
        r = metrics.get(f"class_{label}_recall", "—")
        f = metrics.get(f"class_{label}_f1", "—")
        s = metrics.get(f"class_{label}_support", "—")
        lines.append(f"| {label} | {p} | {r} | {f} | {s} |")
    lines.append("")

    # Confusion matrix
    lines.append("## Confusion Matrix")
    lines.append("")
    matrix = confusion["matrix"]
    lines.append("```")
    lines.append("                Predicted")
    lines.append("                 Neg    Pos")
    lines.append(f"Actual  Neg    {matrix[0][0]:>5}  {matrix[0][1]:>5}")
    lines.append(f"        Pos    {matrix[1][0]:>5}  {matrix[1][1]:>5}")
    lines.append("```")
    lines.append("")
    lines.append(f"- True Negatives: {confusion['true_negatives']}")
    lines.append(f"- False Positives: {confusion['false_positives']}")
    lines.append(f"- False Negatives: {confusion['false_negatives']}")
    lines.append(f"- True Positives: {confusion['true_positives']}")
    lines.append("")

    # ROC curve summary
    lines.append("## ROC Curve")
    lines.append("")
    lines.append(f"- **AUROC**: {roc['auroc']}")
    lines.append(f"- **Curve points**: {len(roc['fpr'])}")
    lines.append("")
    lines.append("| FPR | TPR | Threshold |")
    lines.append("|-----|-----|-----------|")
    for i in range(min(10, len(roc["fpr"]))):
        lines.append(f"| {roc['fpr'][i]} | {roc['tpr'][i]} | {roc['thresholds'][i]} |")
    lines.append("... *(sampled to 100 points for charting)*")
    lines.append("")

    # Threshold analysis
    if threshold_data:
        lines.append("## Per-Threshold Analysis")
        lines.append("")
        lines.append("| Threshold | Precision | Recall | F1 |")
        lines.append("|-----------|-----------|--------|----|")
        for entry in threshold_data:
            lines.append(
                f"| {entry['threshold']} | {entry['precision']} | "
                f"{entry['recall']} | {entry['f1']} |"
            )
        lines.append("")

    # Feature importance
    if fi_data:
        lines.append(f"## Feature Importance (Top {len(fi_data)})")
        lines.append("")
        lines.append("| # | Feature | Weight | Gain | Cover | Importance |")
        lines.append("|---|---------|--------|------|-------|------------|")
        for i, entry in enumerate(fi_data, 1):
            w = entry.get("weight", "—")
            g = entry.get("gain", "—")
            c = entry.get("cover", "—")
            imp = entry.get("importance", 0)
            lines.append(f"| {i} | {entry['feature']} | {w} | {g} | {c} | {imp} |")
        lines.append("")

    # Cross-validation metrics
    if cv:
        lines.append("## Cross-Validation Metrics")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        for key, val in sorted(cv.items()):
            if isinstance(val, float):
                lines.append(f"| {key} | {round(val, 4)} |")
            else:
                lines.append(f"| {key} | {val} |")
        lines.append("")

    return "\n".join(lines)


# Public API


def generate_evaluation_report(
    model: Any,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    model_name: str,
    cv_metrics: dict[str, float] | None = None,
    train_samples: int | None = None,
    save: bool = True,
) -> dict[str, Any]:
    """Generate a comprehensive evaluation report for a trained model.

    Parameters
    ----------
    model : XGBClassifier
        Trained model.
    X_test : pd.DataFrame
        Test features.
    y_test : pd.Series
        Test labels.
    model_name : str
        Model identifier (used for filenames).
    cv_metrics : dict, optional
        Pre-computed cross-validation metrics to include.
    train_samples : int, optional
        Number of training samples.
    save : bool
        If ``True`` (default), saves the report as Markdown and JSON
        alongside the model in the registry.

    Returns
    -------
    dict
        The complete evaluation report.
    """
    report = _generate_report_data(
        model,
        X_test,
        y_test,
        model_name,
        cv_metrics=cv_metrics,
        train_samples=train_samples,
    )

    if save:
        # Markdown
        md_path = _eval_markdown_path(model_name)
        md_content = _report_to_markdown(report)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        logger.info("Evaluation report (Markdown) saved to %s", md_path)

        # JSON
        json_path = _eval_json_path(model_name)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info("Evaluation report (JSON) saved to %s", json_path)

    return report


def load_and_evaluate(
    session,
    model_name: str | None = None,
    save: bool = True,
) -> dict[str, Any] | None:
    """Load a model from the registry and evaluate it against current data.

    Uses the latest model if *model_name* is not specified.
    Generates a fresh evaluation report using the current database state.

    Parameters
    ----------
    session : sqlalchemy.orm.Session
        Database session for feature computation.
    model_name : str, optional
        Name of the model to evaluate. If ``None``, uses the latest.
    save : bool
        If ``True`` (default), saves the report to the registry directory.

    Returns
    -------
    dict or None
        The evaluation report, or ``None`` if no model is available.
    """
    from ml.train import load_risk_model as _load_latest

    if model_name is None:
        model, name = _load_latest()
        if model is None:
            logger.warning("No trained model found. Train a model first.")
            return None
    else:
        # Load specific model by name
        model_b64 = load_model(model_name)
        if model_b64 is None:
            logger.warning("Model '%s' not found in registry.", model_name)
            return None
        import base64

        import xgboost as xgb

        model_bytes = base64.b64decode(model_b64)
        booster = xgb.Booster()
        booster.load_model(bytearray(model_bytes))

        from xgboost import XGBClassifier

        model = XGBClassifier(**DEFAULT_PARAMS)
        model._Booster = booster
        model._le = None
        model.n_classes_ = 2
        name = model_name

    # Compute features and target for test evaluation
    logger.info("Computing features for evaluation...")
    X = compute_all_features(session)
    y = compute_target(session)

    X = X.reindex(columns=FEATURE_NAMES, fill_value=0.0)

    # Filter to students with data
    mask = (X != 0.0).any(axis=1)
    X = X[mask]
    y = y[mask.index[y.index.isin(X.index)]]

    if len(X) < 4:
        logger.warning("Not enough data (%d samples) for meaningful evaluation.", len(X))
        return None

    # Hold out 20% for test evaluation
    from sklearn.model_selection import train_test_split

    _, X_test, _, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    cv_metrics = None
    meta = load_metadata(name)
    if meta and "metrics" in meta:
        cv_metrics = {k: v for k, v in meta["metrics"].items() if k.startswith("cv_")}

    return generate_evaluation_report(
        model,
        X_test,
        y_test,
        name,
        cv_metrics=cv_metrics,
        train_samples=len(X) - len(X_test),
        save=save,
    )


def list_evaluation_reports() -> list[dict[str, Any]]:
    """List all available evaluation reports in the registry.

    Returns
    -------
    list of dict
        Each entry contains model name, report timestamp, and summary metrics.
    """
    reports = []
    for f in sorted(MODELS_DIR.iterdir()):
        if f.name.endswith("_eval.json"):
            try:
                with open(f, encoding="utf-8") as fh:
                    data = json.load(fh)
                meta = data.get("report_metadata", {})
                metrics = data.get("metrics", {})
                reports.append(
                    {
                        "model_name": meta.get("model_name", f.stem.replace("_eval", "")),
                        "generated_at": meta.get("generated_at", ""),
                        "accuracy": metrics.get("accuracy"),
                        "f1": metrics.get("f1"),
                        "auroc": metrics.get("auroc"),
                        "test_samples": meta.get("test_samples"),
                    }
                )
            except (json.JSONDecodeError, OSError) as e:
                logger.debug("Skipping unreadable report %s: %s", f.name, e)
    return reports
