def test_get_risk_students_empty(analytics_service):
    # Empty DB -> empty risk list
    assert analytics_service.get_at_risk_students() == []


def test_attendance_prediction(test_db, analytics_service):
    # If no data, return default
    res = analytics_service.predict_attendance_trend(999)
    assert "trend" in res
    assert "prediction" in res or "prediction_prob" in res
