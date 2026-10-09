"""
Model training module for the ML prediction pipeline.

Trains an XGBoost classifier to predict at-risk students using features
computed from attendance, marks, leaves, and fee data.

Training protocol:
- 80/20 stratified train/test split
- 5-fold cross-validation on training set
- Evaluation: accuracy, AUROC, F1, precision, recall
- Model saved to registry with metrics + metadata
"""

import json
import logging

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, train_test_split
from xgboost import XGBClassifier

from ml.drift import _save_reference_distributions
from ml.features import FEATURE_NAMES, compute_all_features, compute_target
from ml.registry import get_latest_model, load_metadata, load_model, save_model
from utils.time import utc_now

logger = logging.getLogger("ml.train")

# Default training hyperparameters

DEFAULT_PARAMS = {
    "n_estimators": 200,
    "max_depth": 6,
    "learning_rate": 0.1,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": 42,
    "eval_metric": "logloss",
}

RISK_MODEL_NAME = "risk_v1"


def _evaluate_model(
    model: XGBClassifier,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> dict[str, float]:
    """Compute evaluation metrics for the model on test data."""
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "f1": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
        "precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
    }

    # AUROC requires at least one positive and one negative sample
    unique_classes = y_test.nunique()
    if unique_classes >= 2:
        try:
            metrics["auroc"] = round(float(roc_auc_score(y_test, y_proba)), 4)
        except (ValueError, TypeError):
            metrics["auroc"] = 0.0
    else:
        metrics["auroc"] = 0.0

    return metrics


def _cross_validate(
    X: pd.DataFrame,
    y: pd.Series,
    n_splits: int = 5,
) -> dict[str, float]:
    """Run stratified k-fold cross-validation and return average metrics."""
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    fold_metrics: dict[str, list] = {
        "accuracy": [],
        "f1": [],
        "precision": [],
        "recall": [],
        "auroc": [],
    }

    for train_idx, val_idx in skf.split(X, y):
        X_train_fold = X.iloc[train_idx]
        y_train_fold = y.iloc[train_idx]
        X_val_fold = X.iloc[val_idx]
        y_val_fold = y.iloc[val_idx]

        fold_model = XGBClassifier(**DEFAULT_PARAMS)
        fold_model.fit(
            X_train_fold,
            y_train_fold,
            eval_set=[(X_val_fold, y_val_fold)],
            verbose=False,
        )

        y_pred = fold_model.predict(X_val_fold)
        y_proba = fold_model.predict_proba(X_val_fold)[:, 1]

        fold_metrics["accuracy"].append(accuracy_score(y_val_fold, y_pred))
        fold_metrics["f1"].append(f1_score(y_val_fold, y_pred, zero_division=0))
        fold_metrics["precision"].append(precision_score(y_val_fold, y_pred, zero_division=0))
        fold_metrics["recall"].append(recall_score(y_val_fold, y_pred, zero_division=0))
        if y_val_fold.nunique() >= 2:
            try:
                fold_metrics["auroc"].append(roc_auc_score(y_val_fold, y_proba))
            except (ValueError, TypeError):
                fold_metrics["auroc"].append(0.0)
        else:
            fold_metrics["auroc"].append(0.0)

    return {k: round(float(np.mean(v)), 4) if v else 0.0 for k, v in fold_metrics.items()}


def train_risk_model(
    session,
    force_retrain: bool = False,
    test_size: float = 0.2,
) -> tuple[bool, dict[str, float]]:
    """Train or retrain the at-risk student prediction model.

    Parameters
    ----------
    session : sqlalchemy.orm.Session
        Database session for feature computation.
    force_retrain : bool
        If ``True``, retrain even if a model already exists.
    test_size : float
        Fraction of data to hold out for testing (default 0.2).

    Returns
    -------
    (trained : bool, metrics : dict)
        ``trained`` is ``True`` if training was performed.
        ``metrics`` contains evaluation results or an empty dict.
    """
    existing = load_model(RISK_MODEL_NAME)

    if existing and not force_retrain:
        logger.info(
            "Model %s already exists. Use force_retrain=True to retrain.",
            RISK_MODEL_NAME,
        )
        return False, {}

    logger.info("Computing features for all students...")
    X = compute_all_features(session)
    y = compute_target(session)

    # Align feature columns with expected names
    X = X.reindex(columns=FEATURE_NAMES, fill_value=0.0)

    # Filter out students with no data
    mask = (X != 0.0).any(axis=1)
    X = X[mask]
    y = y[mask.index[y.index.isin(X.index)]]

    if len(X) < 10:
        logger.warning("Not enough students with data (%d) to train a meaningful model.", len(X))
        return False, {"error": f"Only {len(X)} students have data; need at least 10."}

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, stratify=y, random_state=42
    )

    logger.info(
        "Training on %d samples, testing on %d samples.",
        len(X_train),
        len(X_test),
    )

    # Train model
    model = XGBClassifier(**DEFAULT_PARAMS)
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    # Cross-validation
    logger.info("Running 5-fold cross-validation...")
    cv_metrics = _cross_validate(X_train, y_train)

    # Test set evaluation
    test_metrics = _evaluate_model(model, X_test, y_test)

    # Combined metrics
    metrics = {"cv_" + k: v for k, v in cv_metrics.items()}
    metrics.update({"test_" + k: v for k, v in test_metrics.items()})
    metrics["train_samples"] = len(X_train)
    metrics["test_samples"] = len(X_test)

    logger.info("Model metrics: %s", json.dumps(metrics, indent=2))

    import base64

    booster = model.get_booster()
    model_bytes = booster.save_raw()
    model_b64 = base64.b64encode(model_bytes).decode("ascii")

    # ── Promotion Gate ────────────────────────────────────────────────────
    # Only promote the new model if its primary metric (AUROC) meets or
    # exceeds the currently active model's. Otherwise save as non-active.
    primary_metric = test_metrics.get("auroc", 0.0)
    current_meta = load_metadata(RISK_MODEL_NAME) if load_model(RISK_MODEL_NAME) else None
    current_auroc = 0.0
    if current_meta and current_meta.get("metrics"):
        current_auroc = current_meta["metrics"].get("test_auroc", 0.0)

    promoted = primary_metric >= current_auroc
    metrics["_promoted"] = promoted
    metrics["_current_active_auroc"] = round(current_auroc, 4)
    metrics["_candidate_auroc"] = round(primary_metric, 4)

    # Generate a unique version name for this candidate
    version_suffix = utc_now().strftime("%Y%m%d_%H%M%S")
    candidate_name = f"{RISK_MODEL_NAME}_candidate_{version_suffix}"

    if promoted:
        # Save as the active model
        save_model(model_b64, RISK_MODEL_NAME, metrics=metrics)
        logger.info(
            "Model %s PROMOTED (AUROC %.4f >= %.4f)",
            RISK_MODEL_NAME,
            primary_metric,
            current_auroc,
        )
    else:
        # Save as a non-active candidate for inspection
        save_model(model_b64, candidate_name, metrics=metrics)
        logger.info(
            "Model %s NOT promoted (AUROC %.4f < %.4f). Saved as %s for inspection.",
            RISK_MODEL_NAME,
            primary_metric,
            current_auroc,
            candidate_name,
        )

    # Save reference feature distributions for drift monitoring
    try:
        _save_reference_distributions(X_train, RISK_MODEL_NAME, metrics=metrics)
        logger.info("Reference distributions saved for drift monitoring.")
    except (RuntimeError, ValueError, OSError) as e:
        logger.warning("Failed to save reference distributions (non-fatal): %s", e)

    # ── Persist promotion decision to DB ──────────────────────────────────
    # Store a structured record so the admin API can serve queryable history.
    try:
        from database.models import PromotionHistory

        active_version = (
            RISK_MODEL_NAME
            if promoted
            else str(current_meta.get("name", RISK_MODEL_NAME)) if current_meta else None
        )
        ph = PromotionHistory(
            candidate_model_version=candidate_name if not promoted else RISK_MODEL_NAME,
            candidate_auroc=round(primary_metric, 4),
            candidate_f1=test_metrics.get("f1"),
            candidate_precision=test_metrics.get("precision"),
            candidate_recall=test_metrics.get("recall"),
            active_model_version=active_version,
            active_auroc=round(current_auroc, 4) if current_meta else None,
            promoted=promoted,
            reason=(
                f"Promoted: candidate AUROC {primary_metric:.4f} >= active AUROC {current_auroc:.4f}"
                if promoted
                else f"Not promoted: candidate AUROC {primary_metric:.4f} < active AUROC {current_auroc:.4f}"
            ),
        )
        session.add(ph)
        session.commit()
    except (OSError, ValueError) as persist_err:
        logger.warning("Failed to persist promotion decision (non-fatal): %s", persist_err)
        session.rollback()

    logger.info(
        "Model training complete. Active model: %s",
        RISK_MODEL_NAME if promoted else candidate_name,
    )
    return True, metrics


def load_risk_model() -> tuple[XGBClassifier | None, str | None]:
    """Load the latest risk prediction model from the registry.

    Returns
    -------
    (XGBClassifier or None, model_name or None)
    """
    import base64

    import xgboost as xgb

    model_name = get_latest_model()
    if not model_name:
        return None, None

    model_b64 = load_model(model_name)
    if not model_b64:
        return None, None

    # Reconstruct: create raw booster, load weights, then attach to XGBClassifier
    model_bytes = base64.b64decode(model_b64)
    booster = xgb.Booster()
    booster.load_model(bytearray(model_bytes))

    # Binary classifier (at-risk vs. not-at-risk), so n_classes is always 2
    model = XGBClassifier(**DEFAULT_PARAMS)
    model._Booster = booster
    model._le = None
    model.n_classes_ = 2
    return model, model_name
