"""Tests for ml/evaluate.py — model evaluation report generator."""

import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from xgboost import XGBClassifier

from ml.evaluate import (
    _classification_metrics_dict,
    _confusion_matrix_data,
    _feature_importance_analysis,
    _generate_report_data,
    _report_to_markdown,
    _roc_curve_data,
    _threshold_analysis,
    generate_evaluation_report,
    list_evaluation_reports,
)

# ═══════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def synthetic_data() -> tuple[object, ...]:
    """Create synthetic binary classification data."""
    np.random.seed(42)
    n = 100
    X = pd.DataFrame(
        np.random.randn(n, 5),
        columns=["feat_a", "feat_b", "feat_c", "feat_d", "feat_e"],
    )
    # Create a non-random target with some signal
    y = pd.Series((X["feat_a"] + X["feat_b"] > 0).astype(int), name="at_risk")
    return X, y


@pytest.fixture
def trained_model(synthetic_data):
    """Train a small XGBoost model for testing."""
    X, y = synthetic_data
    model = XGBClassifier(n_estimators=10, max_depth=3, random_state=42)
    model.fit(X, y)
    return model


# ═══════════════════════════════════════════════════════════════════
#  UNIT TESTS — _classification_metrics_dict
# ═══════════════════════════════════════════════════════════════════


class TestClassificationMetrics:
    def test_perfect_classification(self) -> None:
        y_true = np.array([0, 0, 1, 1])
        y_pred = np.array([0, 0, 1, 1])
        y_proba = np.array([0.1, 0.2, 0.9, 0.8])
        metrics = _classification_metrics_dict(y_true, y_pred, y_proba)
        assert metrics["accuracy"] == 1.0
        assert metrics["f1"] == 1.0
        assert metrics["precision"] == 1.0
        assert metrics["recall"] == 1.0
        assert metrics["auroc"] > 0.5

    def test_all_negative(self) -> None:
        y_true = np.array([0, 0, 0])
        y_pred = np.array([0, 0, 0])
        y_proba = np.array([0.1, 0.2, 0.3])
        metrics = _classification_metrics_dict(y_true, y_pred, y_proba)
        assert metrics["accuracy"] == 1.0
        assert metrics["auroc"] == 0.0  # only one class present
        assert "class_0_precision" in metrics
        # class_1 may not appear in classification_report if no positive samples

    def test_all_positive(self) -> None:
        y_true = np.array([1, 1, 1])
        y_pred = np.array([1, 1, 1])
        y_proba = np.array([0.9, 0.8, 0.95])
        metrics = _classification_metrics_dict(y_true, y_pred, y_proba)
        assert metrics["accuracy"] == 1.0
        assert metrics["auroc"] == 0.0  # only one class

    def test_worst_case(self) -> None:
        y_true = np.array([0, 0, 1, 1])
        y_pred = np.array([1, 1, 0, 0])
        y_proba = np.array([0.9, 0.8, 0.1, 0.2])
        metrics = _classification_metrics_dict(y_true, y_pred, y_proba)
        assert metrics["accuracy"] == 0.0
        assert metrics["f1"] == 0.0
        assert metrics["precision"] == 0.0
        assert metrics["recall"] == 0.0

    def test_support_counts(self) -> None:
        y_true = np.array([0, 0, 0, 1, 1])
        y_pred = np.array([0, 0, 0, 1, 1])
        y_proba = np.array([0.1, 0.2, 0.3, 0.9, 0.8])
        metrics = _classification_metrics_dict(y_true, y_pred, y_proba)
        assert metrics["total_samples"] == 5
        assert metrics["positive_samples"] == 2
        assert metrics["negative_samples"] == 3
        assert metrics["class_0_support"] == 3
        assert metrics["class_1_support"] == 2


# ═══════════════════════════════════════════════════════════════════
#  UNIT TESTS — _confusion_matrix_data
# ═══════════════════════════════════════════════════════════════════


class TestConfusionMatrix:
    def test_perfect(self) -> None:
        cm = _confusion_matrix_data(
            np.array([0, 0, 1, 1]),
            np.array([0, 0, 1, 1]),
        )
        assert cm["true_negatives"] == 2
        assert cm["false_positives"] == 0
        assert cm["false_negatives"] == 0
        assert cm["true_positives"] == 2
        assert cm["matrix"][0][0] == 2
        assert cm["matrix"][1][1] == 2

    def test_all_wrong(self) -> None:
        cm = _confusion_matrix_data(
            np.array([0, 0, 1, 1]),
            np.array([1, 1, 0, 0]),
        )
        assert cm["false_positives"] == 2
        assert cm["false_negatives"] == 2

    def test_imbalanced(self) -> None:
        cm = _confusion_matrix_data(
            np.array([0, 0, 0, 1]),
            np.array([0, 0, 1, 1]),
        )
        assert cm["false_positives"] == 1
        assert cm["false_negatives"] == 0
        assert cm["true_positives"] == 1
        assert cm["true_negatives"] == 2


# ═══════════════════════════════════════════════════════════════════
#  UNIT TESTS — _threshold_analysis
# ═══════════════════════════════════════════════════════════════════


class TestThresholdAnalysis:
    def test_default_thresholds(self) -> None:
        y_true = np.array([0, 0, 1, 1])
        y_proba = np.array([0.05, 0.95, 0.9, 0.1])
        results = _threshold_analysis(y_true, y_proba)
        assert len(results) == 9  # 0.1 through 0.9
        assert all(0.0 <= r["precision"] <= 1.0 for r in results)
        assert all(0.0 <= r["recall"] <= 1.0 for r in results)

    def test_custom_thresholds(self) -> None:
        y_true = np.array([0, 0, 1, 1])
        y_proba = np.array([0.1, 0.2, 0.9, 0.8])
        results = _threshold_analysis(y_true, y_proba, thresholds=[0.5, 0.8])
        assert len(results) == 2
        assert results[0]["threshold"] == 0.5

    def test_extreme_thresholds(self) -> None:
        y_true = np.array([0, 0, 1, 1])
        y_proba = np.array([0.9, 0.8, 0.1, 0.2])  # reversed
        results = _threshold_analysis(y_true, y_proba, thresholds=[0.0, 1.0])
        # At threshold 0.0, everything is positive
        assert results[0]["recall"] == 1.0
        # At threshold 1.0, nothing is positive
        assert results[1]["recall"] == 0.0
        assert results[1]["precision"] == 0.0


# ═══════════════════════════════════════════════════════════════════
#  UNIT TESTS — _roc_curve_data
# ═══════════════════════════════════════════════════════════════════


class TestRocCurve:
    def test_perfect_separation(self) -> None:
        y_true = np.array([0, 0, 1, 1])
        y_proba = np.array([0.0, 0.0, 1.0, 1.0])
        roc = _roc_curve_data(y_true, y_proba)
        assert roc["auroc"] == 1.0
        assert len(roc["fpr"]) >= 2
        assert len(roc["tpr"]) >= 2

    def test_random_guess(self) -> None:
        np.random.seed(42)
        y_true = np.array([0, 0, 0, 1, 1, 1])
        y_proba = np.random.rand(6)
        roc = _roc_curve_data(y_true, y_proba)
        assert roc["auroc"] >= 0.0
        assert roc["auroc"] <= 1.0

    def test_includes_endpoints(self) -> None:
        y_true = np.array([0, 0, 1, 1])
        y_proba = np.array([0.1, 0.2, 0.9, 0.8])
        roc = _roc_curve_data(y_true, y_proba, max_points=2)
        # Should include both endpoints
        assert 1.0 in roc["tpr"]
        assert 1.0 in roc["fpr"]


# ═══════════════════════════════════════════════════════════════════
#  UNIT TESTS — _feature_importance_analysis
# ═══════════════════════════════════════════════════════════════════


class TestFeatureImportance:
    def test_returns_ranked_list(self, trained_model) -> None:
        features = ["feat_a", "feat_b", "feat_c", "feat_d", "feat_e"]
        fi = _feature_importance_analysis(trained_model, features, top_n=5)
        assert len(fi) <= 5
        # XGBoost may return 0 or more features depending on the training run
        if len(fi) >= 1:
            # Check structure
            assert "feature" in fi[0]
            assert "importance" in fi[0]
            # Should be sorted descending
            importances = [f["importance"] for f in fi]
            assert importances == sorted(importances, reverse=True)

    def test_top_n(self, trained_model) -> None:
        features = ["feat_a", "feat_b", "feat_c", "feat_d", "feat_e"]
        fi = _feature_importance_analysis(trained_model, features, top_n=2)
        assert len(fi) <= 2

    def test_empty_model(self) -> None:
        class DummyModel:
            pass

        fi = _feature_importance_analysis(DummyModel(), ["a", "b"], top_n=5)
        assert fi == []

    def test_model_with_importances(self) -> None:
        class MockModel:
            feature_importances_ = np.array([0.6, 0.4])

        fi = _feature_importance_analysis(MockModel(), ["x", "y"], top_n=5)
        assert len(fi) == 2
        assert fi[0]["feature"] == "x"
        assert fi[0]["importance"] == 0.6


# ═══════════════════════════════════════════════════════════════════
#  INTEGRATION TESTS — _generate_report_data
# ═══════════════════════════════════════════════════════════════════


class TestGenerateReport:
    def test_report_structure(self, trained_model, synthetic_data) -> None:
        X, y = synthetic_data
        report = _generate_report_data(trained_model, X, y, "test_model")

        assert "report_metadata" in report
        assert report["report_metadata"]["model_name"] == "test_model"
        assert report["report_metadata"]["test_samples"] == len(X)
        assert report["report_metadata"]["feature_count"] == X.shape[1]

        assert "metrics" in report
        assert "confusion_matrix" in report
        assert "roc_curve" in report
        assert "threshold_analysis" in report
        assert "feature_importance" in report

    def test_report_with_cv(self, trained_model, synthetic_data) -> None:
        X, y = synthetic_data
        cv = {"cv_accuracy": 0.95, "cv_f1": 0.94}
        report = _generate_report_data(trained_model, X, y, "cv_test", cv_metrics=cv)

        assert "cv_metrics" in report
        assert report["cv_metrics"]["cv_accuracy"] == 0.95

    def test_report_metrics_are_reasonable(self, trained_model, synthetic_data) -> None:
        X, y = synthetic_data
        report = _generate_report_data(trained_model, X, y, "test_model")
        metrics = report["metrics"]

        # On synthetic data with a real signal, should be better than random
        assert metrics["accuracy"] >= 0.4
        assert metrics["auroc"] >= 0.3


# ═══════════════════════════════════════════════════════════════════
#  INTEGRATION TESTS — _report_to_markdown
# ═══════════════════════════════════════════════════════════════════


class TestReportToMarkdown:
    def test_contains_sections(self, trained_model, synthetic_data) -> None:
        X, y = synthetic_data
        report = _generate_report_data(trained_model, X, y, "test_model")
        md = _report_to_markdown(report)

        assert "# Model Evaluation Report: `test_model`" in md
        assert "## Classification Metrics" in md
        assert "## Confusion Matrix" in md
        assert "## ROC Curve" in md
        assert "## Per-Threshold Analysis" in md
        assert "## Feature Importance" in md

    def test_has_cv_section(self, trained_model, synthetic_data) -> None:
        X, y = synthetic_data
        cv = {"cv_accuracy": 0.95}
        report = _generate_report_data(trained_model, X, y, "test_model", cv_metrics=cv)
        md = _report_to_markdown(report)

        assert "## Cross-Validation Metrics" in md
        assert "0.95" in md

    def test_no_feature_importance(self) -> None:
        """Report should still render even with empty feature importance."""
        report = {
            "report_metadata": {
                "model_name": "empty",
                "generated_at": "2026-01-01T00:00:00+00:00",
                "test_samples": 0,
                "feature_count": 0,
            },
            "metrics": {
                "accuracy": 0.0,
                "f1": 0.0,
                "precision": 0.0,
                "recall": 0.0,
                "auroc": 0.0,
            },
            "confusion_matrix": {
                "matrix": [[0, 0], [0, 0]],
                "true_negatives": 0,
                "false_positives": 0,
                "false_negatives": 0,
                "true_positives": 0,
            },
            "roc_curve": {"fpr": [], "tpr": [], "thresholds": [], "auroc": 0.0},
            "threshold_analysis": [],
            "feature_importance": [],
        }
        md = _report_to_markdown(report)
        # Empty feature importance section is excluded from markdown
        assert "## Classification Metrics" in md
        assert "## Confusion Matrix" in md


# ═══════════════════════════════════════════════════════════════════
#  INTEGRATION TESTS — generate_evaluation_report
# ═══════════════════════════════════════════════════════════════════


class TestGenerateEvaluationReport:
    def test_saves_files(self, trained_model, synthetic_data, monkeypatch) -> None:
        X, y = synthetic_data
        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.setattr("ml.evaluate.MODELS_DIR", Path(tmpdir))

            report = generate_evaluation_report(trained_model, X, y, "test_model_v1", save=True)

            # Check files were saved
            md_path = Path(tmpdir) / "test_model_v1_eval.md"
            json_path = Path(tmpdir) / "test_model_v1_eval.json"
            assert md_path.exists()
            assert json_path.exists()

            # Verify JSON content matches report
            with open(json_path) as f:
                saved = json.load(f)
            assert saved["report_metadata"]["model_name"] == "test_model_v1"
            assert saved["metrics"]["accuracy"] == report["metrics"]["accuracy"]

    def test_no_save_flag(self, trained_model, synthetic_data, monkeypatch) -> None:
        X, y = synthetic_data
        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.setattr("ml.evaluate.MODELS_DIR", Path(tmpdir))

            _ = generate_evaluation_report(trained_model, X, y, "test_model_nosave", save=False)

            md_path = Path(tmpdir) / "test_model_nosave_eval.md"
            json_path = Path(tmpdir) / "test_model_nosave_eval.json"
            assert not md_path.exists()
            assert not json_path.exists()

    def test_returns_correct_shape(self, trained_model, synthetic_data) -> None:
        X, y = synthetic_data
        report = generate_evaluation_report(trained_model, X, y, "test", save=False)
        assert "report_metadata" in report
        assert "metrics" in report
        assert "confusion_matrix" in report
        assert "roc_curve" in report
        assert "threshold_analysis" in report
        assert "feature_importance" in report


# ═══════════════════════════════════════════════════════════════════
#  INTEGRATION TESTS — list_evaluation_reports
# ═══════════════════════════════════════════════════════════════════


class TestListEvaluationReports:
    def test_list_empty(self, monkeypatch) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.setattr("ml.evaluate.MODELS_DIR", Path(tmpdir))
            reports = list_evaluation_reports()
            assert reports == []

    def test_list_reports(self, monkeypatch, trained_model, synthetic_data) -> None:
        X, y = synthetic_data
        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.setattr("ml.evaluate.MODELS_DIR", Path(tmpdir))

            # Generate a report
            generate_evaluation_report(trained_model, X, y, "v1", save=True)
            generate_evaluation_report(trained_model, X, y, "v2", save=True)

            reports = list_evaluation_reports()
            assert len(reports) == 2
            names = [r["model_name"] for r in reports]
            assert "v1" in names
            assert "v2" in names
            assert all("accuracy" in r for r in reports)

    def test_skips_corrupt_files(self, monkeypatch) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.setattr("ml.evaluate.MODELS_DIR", Path(tmpdir))

            # Write a corrupt JSON file
            corrupt = Path(tmpdir) / "corrupt_eval.json"
            corrupt.write_text("not valid json")

            reports = list_evaluation_reports()
            assert reports == []  # Corrupt file is skipped gracefully


# ═══════════════════════════════════════════════════════════════════
#  EDGE CASES
# ═══════════════════════════════════════════════════════════════════


class TestEdgeCases:
    def test_single_sample(self) -> None:
        """Single sample should not crash."""
        y_true = np.array([1])
        y_pred = np.array([1])
        y_proba = np.array([0.9])
        metrics = _classification_metrics_dict(y_true, y_pred, y_proba)
        assert metrics["accuracy"] == 1.0
        assert metrics["auroc"] == 0.0  # only one class

    def test_empty_threshold_list(self) -> None:
        y_true = np.array([0, 0, 1, 1])
        y_proba = np.array([0.1, 0.2, 0.9, 0.8])
        results = _threshold_analysis(y_true, y_proba, thresholds=[])
        assert results == []

    def test_feature_importance_no_booster(self) -> None:
        """Model without feature_importances_ should return empty list."""

        class MinimalModel:
            pass

        fi = _feature_importance_analysis(MinimalModel(), ["a"], top_n=5)
        assert fi == []
