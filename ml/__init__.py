"""
Binary Brain Institute Management System — ML Module

Provides ML-powered risk prediction, grade forecasting, and attendance
trend analysis using XGBoost with SHAP explainability.

Package structure::

    ml/
    ├── __init__.py      # Package init
    ├── features.py      # Feature engineering pipeline
    ├── registry.py      # Model versioning (file-based, swappable to MLflow)
    ├── train.py         # XGBoost training with cross-validation
    ├── explain.py       # SHAP-based prediction explanations
    └── service.py       # Unified MLService orchestration
"""

ML_PACKAGE_VERSION = "1.0.0"
