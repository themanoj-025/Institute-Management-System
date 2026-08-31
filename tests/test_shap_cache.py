"""SHAP explainer cache tests.

Tests cover:
1. The cached explainer is returned on subsequent calls with same model_version
2. Cache invalidates and rebuilds when model_version changes
3. Cache miss (first call) creates and caches the explainer
"""

from unittest.mock import MagicMock, patch

import numpy as np

from ml.explain import _explainer_cache, _get_cached_explainer, invalidate_explainer_cache


class TestShapExplainerCache:
    """Test the SHAP TreeExplainer caching mechanism."""

    def setup_method(self) -> None:
        """Clear cache before each test."""
        _explainer_cache.clear()

    def test_cache_returns_same_instance_for_same_version(self) -> None:
        """The cached explainer should be returned on subsequent calls with same version."""
        mock_explainer = MagicMock()
        mock_explainer.shap_values.return_value = np.array([[0.1, -0.2, 0.3]])

        mock_model = MagicMock()

        with patch("ml.explain._build_explainer", return_value=mock_explainer) as mock_build:
            # First call: should build a new explainer
            result1 = _get_cached_explainer(mock_model, model_version="risk_v1")
            assert mock_build.call_count == 1

            # Second call with same version: should use cache
            result2 = _get_cached_explainer(mock_model, model_version="risk_v1")
            assert mock_build.call_count == 1  # Should not have called _build_explainer again

            assert result1 is result2  # Same instance

    def test_cache_miss_on_version_change(self) -> None:
        """Cache should miss when model_version changes, building a new explainer."""
        mock_explainer_v1 = MagicMock()
        mock_explainer_v2 = MagicMock()

        mock_model = MagicMock()

        def _build_side_effect(model):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_explainer_v1
            return mock_explainer_v2

        call_count = 0

        with patch("ml.explain._build_explainer", side_effect=_build_side_effect) as mock_build:
            # First version
            result1 = _get_cached_explainer(mock_model, model_version="risk_v1")
            assert mock_build.call_count == 1

            # Different version — should build again
            result2 = _get_cached_explainer(mock_model, model_version="risk_v2")
            assert mock_build.call_count == 2

            assert result1 is not result2  # Different instances

    def test_no_version_skips_cache(self) -> None:
        """When model_version is None, caching should be skipped."""
        mock_explainer1 = MagicMock()
        mock_explainer2 = MagicMock()
        call_count = [0]

        def _side_effect(model):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_explainer1
            return mock_explainer2

        with patch("ml.explain._build_explainer", side_effect=_side_effect) as mock_build:
            result1 = _get_cached_explainer(MagicMock(), model_version=None)
            assert mock_build.call_count == 1

            # Second call without version should also build new
            result2 = _get_cached_explainer(MagicMock(), model_version=None)
            assert mock_build.call_count == 2

            assert result1 is not result2

    def test_invalidate_specific_version(self) -> None:
        """Invalidating a specific version should remove only that entry."""
        mock_explainer = MagicMock()

        with patch("ml.explain._build_explainer", return_value=mock_explainer):
            _get_cached_explainer(MagicMock(), model_version="risk_v1")
            _get_cached_explainer(MagicMock(), model_version="risk_v2")

            assert len(_explainer_cache) == 2

            # Invalidate only v1
            invalidate_explainer_cache(model_version="risk_v1")
            assert "risk_v1" not in _explainer_cache
            assert "risk_v2" in _explainer_cache

    def test_invalidate_all_versions(self) -> None:
        """Invalidating without version should clear the entire cache."""
        mock_explainer = MagicMock()

        with patch("ml.explain._build_explainer", return_value=mock_explainer):
            _get_cached_explainer(MagicMock(), model_version="risk_v1")
            _get_cached_explainer(MagicMock(), model_version="risk_v2")

            assert len(_explainer_cache) == 2

            # Clear all
            invalidate_explainer_cache()
            assert len(_explainer_cache) == 0

    def test_cache_rebuilds_after_invalidation(self) -> None:
        """After invalidation, the next call should rebuild the cache."""
        mock_explainer = MagicMock()

        with patch("ml.explain._build_explainer", return_value=mock_explainer) as mock_build:
            _get_cached_explainer(MagicMock(), model_version="risk_v1")
            assert mock_build.call_count == 1

            # Invalidate
            invalidate_explainer_cache(model_version="risk_v1")
            assert "risk_v1" not in _explainer_cache

            # Rebuild
            _get_cached_explainer(MagicMock(), model_version="risk_v1")
            assert mock_build.call_count == 2

    def test_build_explainer_fails_gracefully(self) -> None:
        """If _build_explainer fails, it should return None without raising."""
        model = MagicMock()

        with patch("ml.explain._build_explainer", return_value=None):
            result = _get_cached_explainer(model, model_version="risk_v1")
            assert result is None

    def test_concurrent_access_safety(self) -> None:
        """The cache should be safe for concurrent access from threads."""
        import threading

        mock_explainer = MagicMock()
        results = []

        def access_cache(version) -> None:
            with patch("ml.explain._build_explainer", return_value=mock_explainer):
                result = _get_cached_explainer(MagicMock(), model_version=version)
                results.append(result)

        threads = []
        for i in range(10):
            t = threading.Thread(target=access_cache, args=(f"risk_v{i % 2}",))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All threads for the same version should get the same instance
        assert len(_explainer_cache) == 2  # Two versions cached
        assert results[0] is not None
