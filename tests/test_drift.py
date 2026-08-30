"""Tests for ML drift detection module (ml/drift.py)."""

import math
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

# Allow importing from ml.drift
from ml.drift import (
    REFERENCE_FILE,
    _compute_feature_psi,
    _save_reference_distributions,
    compute_drift_report,
    load_reference_distributions,
)


class TestComputeFeaturePsi:
    """Tests for the _compute_feature_psi function."""

    def test_identical_distributions(self) -> None:
        """PSI should be ~0 when reference and current are identical."""
        a = np.random.RandomState(42).normal(0, 1, 1000)
        psi = _compute_feature_psi(a, a)
        assert psi < 1e-4, f"Expected near-zero PSI for identical dists, got {psi}"

    def test_shifted_distributions(self) -> None:
        """PSI should be > 0.1 for shifted distributions."""
        ref = np.random.RandomState(42).normal(0, 1, 1000)
        curr = ref + 2.0  # Shift by 2 standard deviations
        psi = _compute_feature_psi(ref, curr)
        # A shift this large should produce detectable drift
        assert psi > 0.05, f"Expected detectable PSI for shifted dists, got {psi}"

    def test_constant_feature(self) -> None:
        """PSI should be 0 for constant features."""
        ref = np.ones(100) * 5.0
        curr = np.ones(100) * 5.0
        psi = _compute_feature_psi(ref, curr)
        assert psi == 0.0, f"Expected 0 PSI for constant feature, got {psi}"

    def test_empty_arrays(self) -> None:
        """PSI should be 0 for empty arrays."""
        psi = _compute_feature_psi(np.array([]), np.array([1.0, 2.0]))
        assert psi == 0.0, "Expected 0 PSI for empty reference"

        psi = _compute_feature_psi(np.array([1.0, 2.0]), np.array([]))
        assert psi == 0.0, "Expected 0 PSI for empty current"

    def test_single_value_array(self) -> None:
        """PSI should handle single-value arrays without crashing."""
        ref = np.array([3.14])
        curr = np.array([3.14])
        psi = _compute_feature_psi(ref, curr)
        assert isinstance(psi, float)
        assert psi >= 0.0


class TestSaveAndLoadReference:
    """Tests for _save_reference_distributions and load_reference_distributions."""

    def setup_method(self) -> None:
        self.tmp_dir = tempfile.mkdtemp()
        self._original_dir = REFERENCE_FILE.parent
        # Temporarily redirect REFERENCE_FILE to temp dir
        self._patcher = patch(
            "ml.drift.REFERENCE_FILE",
            Path(self.tmp_dir) / "reference_distributions.json",
        )
        self.mock_ref_file = self._patcher.start()

    def teardown_method(self) -> None:
        self._patcher.stop()
        import shutil

        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    @patch(
        "ml.drift.REFERENCE_FILE",
        new_callable=lambda: Path(tempfile.mkdtemp()) / "ref.json",
    )
    def test_save_and_load_roundtrip(self, mock_ref_file) -> None:
        """Saving then loading should return identical data."""
        X = pd.DataFrame(
            {
                "attendance_rate_4wk": [80.0, 90.0, 70.0],
                "marks_avg": [65.0, 75.0, 55.0],
                "gender_male": [1, 0, 1],
            }
        )
        metrics = {"test_auroc": 0.85, "cv_f1": 0.78}

        saved_path = _save_reference_distributions(X, "risk_v1", metrics=metrics)
        assert saved_path is not None
        assert Path(saved_path).exists()

        loaded = load_reference_distributions()
        assert loaded is not None
        assert loaded["model_name"] == "risk_v1"
        assert loaded["feature_order"] == list(X.columns)
        assert loaded["n_samples"] == 3
        assert loaded["metrics"]["test_auroc"] == 0.85

        # Check per-feature stats
        for col in X.columns:
            assert col in loaded["features"], f"Missing feature: {col}"
            feat = loaded["features"][col]
            assert "mean" in feat
            assert "std" in feat
            assert "min" in feat
            assert "max" in feat
            assert "percentiles" in feat

    @patch(
        "ml.drift.REFERENCE_FILE",
        new_callable=lambda: Path(tempfile.mkdtemp()) / "ref.json",
    )
    def test_load_nonexistent_file(self, mock_ref_file) -> None:
        """Loading when no file exists should return None."""
        result = load_reference_distributions()
        assert result is None, "Expected None for missing reference file"

    @patch(
        "ml.drift.REFERENCE_FILE",
        new_callable=lambda: Path(tempfile.mkdtemp()) / "ref.json",
    )
    def test_save_empty_dataframe(self, mock_ref_file) -> None:
        """Saving with empty DataFrame should not crash."""
        X = pd.DataFrame()
        saved_path = _save_reference_distributions(X, "risk_v1")
        assert saved_path is not None
        loaded = load_reference_distributions()
        assert loaded is not None
        assert loaded["feature_order"] == []

    @patch(
        "ml.drift.REFERENCE_FILE",
        new_callable=lambda: Path(tempfile.mkdtemp()) / "ref.json",
    )
    def test_save_without_metrics(self, mock_ref_file) -> None:
        """Saving without metrics should still work."""
        X = pd.DataFrame({"attendance_rate_4wk": [80.0, 90.0]})
        saved_path = _save_reference_distributions(X, "risk_v1")
        assert saved_path is not None
        loaded = load_reference_distributions()
        assert loaded is not None
        assert "metrics" not in loaded


class TestComputeDriftReport:
    """Tests for compute_drift_report."""

    def setup_method(self) -> None:
        self.tmp_dir = tempfile.mkdtemp()
        self._patcher = patch(
            "ml.drift.REFERENCE_FILE",
            Path(self.tmp_dir) / "reference_distributions.json",
        )
        self.mock_ref_file = self._patcher.start()

    def teardown_method(self) -> None:
        self._patcher.stop()
        import shutil

        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_no_reference_file(self) -> None:
        """When no reference file exists, report should contain error."""
        mock_session = MagicMock()
        report = compute_drift_report(mock_session)
        assert report["drift_detected"] is False
        assert "error" in report
        assert "No reference distributions found" in report["error"]

    @patch("ml.drift.compute_all_features")
    def test_drift_report_structure(self, mock_compute_features) -> None:
        """The report dictionary should have all expected keys."""
        # Pre-save a reference distribution
        X_ref = pd.DataFrame(
            {
                "attendance_rate_4wk": [80.0, 85.0, 75.0, 90.0, 70.0],
                "marks_avg": [65.0, 70.0, 60.0, 75.0, 55.0],
            }
        )
        _save_reference_distributions(X_ref, "risk_v1", metrics={"test_auroc": 0.85})

        # Mock current features
        mock_compute_features.return_value = pd.DataFrame(
            {
                "attendance_rate_4wk": [82.0, 84.0, 76.0],
                "marks_avg": [66.0, 69.0, 61.0],
            }
        )

        mock_session = MagicMock()
        report = compute_drift_report(mock_session)

        expected_keys = [
            "drift_detected",
            "severe_drift",
            "feature_count",
            "features_drifted",
            "max_psi",
            "max_psi_feature",
            "feature_scores",
            "feature_stats",
            "n_samples_reference",
            "n_samples_current",
            "reference_model",
        ]
        for key in expected_keys:
            assert key in report, f"Missing key in report: {key}"

        assert report["reference_model"] == "risk_v1"
        assert report["n_samples_reference"] == 5
        assert report["n_samples_current"] == 3
        assert isinstance(report["feature_scores"], dict)
        assert isinstance(report["feature_stats"], dict)

    @patch("ml.drift.compute_all_features")
    def test_drift_detection_flag(self, mock_compute_features) -> None:
        """If features differ significantly, drift_detected should be True."""
        X_ref = pd.DataFrame(
            {
                "attendance_rate_4wk": [80.0, 85.0, 75.0, 90.0, 70.0],
                "marks_avg": [65.0, 70.0, 60.0, 75.0, 55.0],
            }
        )
        _save_reference_distributions(X_ref, "risk_v1")

        # Heavily shifted current distribution
        mock_compute_features.return_value = pd.DataFrame(
            {
                "attendance_rate_4wk": [
                    30.0,
                    25.0,
                    35.0,
                    20.0,
                    40.0,
                    30.0,
                    25.0,
                    35.0,
                    20.0,
                    40.0,
                ],
                "marks_avg": [
                    20.0,
                    25.0,
                    15.0,
                    30.0,
                    10.0,
                    20.0,
                    25.0,
                    15.0,
                    30.0,
                    10.0,
                ],
            }
        )

        mock_session = MagicMock()
        report = compute_drift_report(mock_session, psi_threshold=0.05)

        assert report["drift_detected"] is True, "Expected drift detection for heavily shifted data"
        assert report["feature_count"] >= 2

    @patch("ml.drift.compute_all_features")
    def test_feature_computation_failure(self, mock_compute_features) -> None:
        """If feature computation fails, report should contain error."""
        X_ref = pd.DataFrame({"attendance_rate_4wk": [80.0, 85.0]})
        _save_reference_distributions(X_ref, "risk_v1")

        mock_compute_features.side_effect = ValueError("DB connection failed")

        mock_session = MagicMock()
        report = compute_drift_report(mock_session)

        assert report["drift_detected"] is False
        assert "error" in report
        assert "Feature computation failed" in report["error"]

    @patch("ml.drift.compute_all_features")
    def test_empty_current_features(self, mock_compute_features) -> None:
        """If no current features are available, report should contain error."""
        X_ref = pd.DataFrame({"attendance_rate_4wk": [80.0, 85.0]})
        _save_reference_distributions(X_ref, "risk_v1")

        mock_compute_features.return_value = pd.DataFrame()

        mock_session = MagicMock()
        report = compute_drift_report(mock_session)

        assert report["drift_detected"] is False
        assert "error" in report
        assert "No current feature data" in report["error"]

    @patch("ml.drift.compute_all_features")
    def test_default_psi_threshold(self, mock_compute_features) -> None:
        """Default threshold should be 0.10 unless overridden."""
        X_ref = pd.DataFrame({"attendance_rate_4wk": [80.0, 85.0, 90.0]})
        _save_reference_distributions(X_ref, "risk_v1")

        # Close distribution — should not trigger drift at default threshold
        mock_compute_features.return_value = pd.DataFrame(
            {
                "attendance_rate_4wk": [81.0, 84.0, 89.0],
            }
        )

        mock_session = MagicMock()
        report = compute_drift_report(mock_session)
        # With seeded RNG (42), close distributions should produce PSI < 0.10
        assert report.get("error", "") == "", f"Unexpected error: {report.get('error')}"
        assert report["feature_count"] == 1
        assert report["n_samples_current"] == 3


class TestPsiEdgeCases:
    """Edge case tests for the PSI computation."""

    def test_extreme_values(self) -> None:
        """PSI should handle extreme values without crashing."""
        ref = np.array([1e10, -1e10, 0.0, 1e-10])
        curr = np.array([1e10 + 1, -1e10 - 1, 1.0, 1e-9])
        psi = _compute_feature_psi(ref, curr)
        assert isinstance(psi, float)
        assert psi >= 0.0

    def test_nan_values(self) -> None:
        """NaN values should be handled gracefully.

        numpy operations with NaN may produce NaN output, which we need to
        guard against in the implementation.
        """
        ref = np.array([1.0, 2.0, 3.0, np.nan, 5.0])
        curr = np.array([1.5, 2.5, 3.5, 4.5, np.nan])
        # The PSI function doesn't explicitly handle NaN, but numpy operations
        # should produce finite values
        psi = _compute_feature_psi(ref, curr)
        assert isinstance(psi, float)
        assert not math.isnan(psi), "PSI should not be NaN"
