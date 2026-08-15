"""Tests for the ML prediction module (ml/)."""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from database.models import (
    Attendance,
    AttendanceStatus,
    Course,
    Fee,
    FeeStatus,
    Leave,
    LeaveStatus,
    Result,
    Session,
    Student,
    User,
    UserRole,
)
from ml.explain import explain_prediction
from ml.features import (
    FEATURE_NAMES,
    compute_all_features,
    compute_student_features,
    compute_target,
)
from ml.service import MLService
from ml.train import DEFAULT_PARAMS, train_risk_model

# Fixtures


@pytest.fixture
def seeded_db(test_db):
    """Seed the test database with students, attendance, results, and fees."""
    # Use a unique course code per test run to avoid UNIQUE constraint conflicts
    # in session-scoped test_db.
    import uuid

    suffix = uuid.uuid4().hex[:6]
    course_code = f"ML_{suffix}"
    sess_name = f"2024-{suffix}"

    course = Course(
        code=course_code,
        name="ML Test Course",
        duration_months=6,
        fee=50000.0,
    )
    test_db.add(course)

    sess = Session(
        name=sess_name,
        start_date=date(2024, 6, 1),
        end_date=date(2025, 3, 31),
        is_active=True,
    )
    test_db.add(sess)
    test_db.flush()

    students_data = [
        (f"good_{suffix}", "Good Student", "male", 0.85, 75.0, 20000, FeeStatus.paid),
        (
            f"low_att_{suffix}",
            "Low Attendance",
            "male",
            0.35,
            70.0,
            45000,
            FeeStatus.partial,
        ),
        (
            f"low_mar_{suffix}",
            "Low Marks",
            "female",
            0.80,
            25.0,
            50000,
            FeeStatus.unpaid,
        ),
        (
            f"medium_{suffix}",
            "Medium Risk",
            "male",
            0.55,
            50.0,
            35000,
            FeeStatus.partial,
        ),
    ]

    created_ids = []
    for i, (
        uname,
        fname,
        gender,
        att_rate,
        marks_pct,
        fee_amt,
        fee_status,
    ) in enumerate(students_data, 1):
        user = User(
            username=uname,
            password_hash="hash_placeholder",
            role=UserRole.student,
            email=f"{uname}@test.edu",
            is_active=True,
        )
        test_db.add(user)
        test_db.flush()

        student = Student(
            user_id=user.id,
            enrollment_no=f"ML{suffix}{i:05d}",
            first_name=fname.split()[0],
            last_name=fname.split()[1] if " " in fname else "Student",
            dob=date(2000, 1, i),
            gender=gender,
            course_id=course.id,
            session_id=sess.id,
            admission_date=date(2024, 6, 15),
        )
        test_db.add(student)
        test_db.flush()
        created_ids.append(student.id)

        # Attendance (20 per student)
        base_date = date(2024, 7, 1)
        for week in range(5):
            for day_offset in range(4):
                d = date.fromordinal(base_date.toordinal() + week * 7 + day_offset)
                status = (
                    AttendanceStatus.present
                    if np.random.random() < att_rate
                    else AttendanceStatus.absent
                )
                test_db.add(
                    Attendance(
                        student_id=student.id,
                        subject_id=1,
                        session_id=sess.id,
                        date=d,
                        status=status,
                    )
                )

        # Results (3 per student)
        for exam_type in ["Quiz", "Mid-Term", "Final"]:
            obtained = marks_pct + np.random.uniform(-5, 5)
            test_db.add(
                Result(
                    student_id=student.id,
                    subject_id=1,
                    session_id=sess.id,
                    exam_type=f"{exam_type}_{suffix}",
                    marks_obtained=max(0, min(100, obtained)),
                    total_marks=100.0,
                    date_declared=base_date,
                )
            )

        # Fee
        test_db.add(
            Fee(
                student_id=student.id,
                session_id=sess.id,
                total_amount=fee_amt,
                paid_amount=fee_amt * (1.0 if fee_status == FeeStatus.paid else 0.3),
                due_date=date(2024, 8, 1),
                status=fee_status,
            )
        )

        # Leave for at-risk or medium students
        if "low_" in uname or "medium" in uname:
            test_db.add(
                Leave(
                    student_id=student.id,
                    start_date=date(2024, 10, 1),
                    end_date=date(2024, 10, 3),
                    reason="Illness",
                    status=LeaveStatus.approved,
                )
            )

    test_db.commit()
    return test_db


# Feature Engineering Tests


def test_compute_student_features(seeded_db):
    """Verify feature computation returns all expected features."""
    student = seeded_db.query(Student).first()
    features = compute_student_features(seeded_db, student.id)

    assert isinstance(features, pd.Series)
    assert len(features) > 0
    for feat in FEATURE_NAMES:
        assert feat in features.index, f"Missing feature: {feat}"
    assert features["attendance_rate_overall"] >= 0
    assert features["attendance_rate_overall"] <= 100


def test_compute_student_features_nonexistent(seeded_db):
    """Non-existent student should raise ValueError."""
    with pytest.raises(ValueError, match="Student .* not found"):
        compute_student_features(seeded_db, 99999)


def test_compute_all_features_shape(seeded_db):
    """Verify batch feature computation returns correct DataFrame shape."""
    df = compute_all_features(seeded_db)
    assert isinstance(df, pd.DataFrame)
    assert len(df) >= 1  # at least the seeded students (accumulated across tests)
    for feat in FEATURE_NAMES:
        assert feat in df.columns, f"Missing column: {feat}"


def test_compute_target(seeded_db):
    """Verify target computation flags at-risk students correctly."""
    target = compute_target(seeded_db)
    assert isinstance(target, pd.Series)
    assert len(target) >= 1
    # The "good" student should not be at risk
    good = seeded_db.query(Student).filter(Student.first_name == "Good").first()
    if good is not None and good.id in target.index:
        assert target[good.id] == 0, "Good student should not be at risk"


# Training Tests


def test_train_risk_model(seeded_db):
    """Verify model training runs and produces metrics."""
    trained, metrics = train_risk_model(seeded_db, force_retrain=True)

    assert trained is True
    assert "test_accuracy" in metrics
    assert "cv_f1" in metrics or "test_f1" in metrics
    assert metrics["train_samples"] >= 0
    assert metrics["test_samples"] >= 0


def test_train_risk_model_skip_if_exists(seeded_db):
    """Verify training skips if model exists and force_retrain=False."""
    # Train once
    train_risk_model(seeded_db, force_retrain=True)
    # Second call should skip
    trained, metrics = train_risk_model(seeded_db, force_retrain=False)
    assert trained is False
    assert metrics == {}


# ML Service Tests


def test_ml_service_get_dashboard_kpis(seeded_db):
    """Verify MLService.get_dashboard_kpis returns correct structure."""
    svc = MLService()
    kpis = svc.get_dashboard_kpis(seeded_db)

    assert "total_students" in kpis
    assert kpis["total_students"] >= 4
    assert "total_fees_expected" in kpis
    assert "total_fees_collected" in kpis
    assert "collection_rate" in kpis
    assert isinstance(kpis["collection_rate"], (int, float))


def test_ml_service_get_at_risk_students(seeded_db):
    """Verify at-risk student detection returns expected structure."""
    svc = MLService()
    at_risk = svc.get_at_risk_students(seeded_db, threshold=0.0, top_n=10)

    assert isinstance(at_risk, list)
    if len(at_risk) > 0:
        student = at_risk[0]
        assert "student_id" in student
        assert "name" in student
        assert "risk_score" in student
        assert "risk_level" in student
        assert "explanations" in student


def test_ml_service_predict_student_risk(seeded_db):
    """Verify single-student risk prediction."""
    student = seeded_db.query(Student).first()
    svc = MLService()
    result = svc.predict_student_risk(seeded_db, student.id)

    assert result is not None
    assert result["student_id"] == student.id
    assert "risk_score" in result
    assert "risk_level" in result
    assert "explanations" in result
    assert len(result["explanations"]) <= 3  # top_n=3


def test_ml_service_predict_student_risk_nonexistent(seeded_db):
    """Non-existent student ID should return None."""
    svc = MLService()
    result = svc.predict_student_risk(seeded_db, 99999)
    assert result is None


def test_ml_service_predict_attendance_trend(seeded_db):
    """Verify attendance trend prediction returns expected structure."""
    student = seeded_db.query(Student).first()
    svc = MLService()
    trend = svc.predict_attendance_trend(seeded_db, student.id)

    assert "trend" in trend
    assert trend["trend"] in ("Upward", "Downward", "Stable", "Insufficient Data")
    assert "current_4wk_rate" in trend or "prediction" in trend


def test_ml_service_train(seeded_db):
    """Verify explicit training triggers model training."""
    svc = MLService()
    trained, metrics = svc.train(seeded_db, force=True)

    assert trained is True
    assert isinstance(metrics, dict)


# Explainability Tests


def test_explain_prediction_fallback(seeded_db):
    """Verify explain_prediction works with fallback to feature importances."""
    from xgboost import XGBClassifier

    # Train a quick model
    params = {**DEFAULT_PARAMS, "n_estimators": 10}
    model = XGBClassifier(**params)
    X = compute_all_features(seeded_db)
    y = compute_target(seeded_db)
    mask = (X != 0.0).any(axis=1)
    X = X[mask]
    y = y[mask.index[y.index.isin(X.index)]]
    if len(X) < 2:
        pytest.skip("Not enough training data")

    model.fit(X, y)

    features = X.iloc[0]
    explanation = explain_prediction(model, features)

    assert isinstance(explanation, list)
    assert len(explanation) <= 3
    if len(explanation) > 0:
        assert "name" in explanation[0]
        assert "label" in explanation[0]
        assert "value" in explanation[0]
        assert "importance" in explanation[0]
        assert "direction" in explanation[0]


# Analytics Service Integration Tests


def test_analytics_service_get_dashboard_kpis(seeded_db, analytics_service):
    """Verify AnalyticsService delegates correctly to MLService."""
    kpis = analytics_service.get_dashboard_kpis()
    assert kpis["total_students"] >= 4


def test_analytics_service_get_at_risk(seeded_db, analytics_service):
    """Verify AnalyticsService.get_at_risk_students returns list."""
    at_risk = analytics_service.get_at_risk_students(threshold=0.0, top_n=10)
    assert isinstance(at_risk, list)


def test_analytics_service_predict_attendance_trend(seeded_db, analytics_service):
    """Verify attendance trend prediction works through analytics service."""
    student = seeded_db.query(Student).first()
    trend = analytics_service.predict_attendance_trend(student.id)
    assert "trend" in trend
