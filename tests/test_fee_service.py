"""Tests for FeeService with soft-delete support."""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.db_session import Base
from database.models import Course, Fee, FeePayment, FeeStatus, Session, Student, User, UserRole
from services.fee_service import FeeService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def seeded_db(db_session):
    course = Course(code="CS101", name="CS Basics", duration_months=6, fee=50000)
    db_session.add(course)
    sess = Session(name="2024", start_date=date(2024, 1, 1), end_date=date(2024, 12, 31))
    db_session.add(sess)
    db_session.flush()

    user = User(
        username="fee_stu",
        password_hash="hash",
        role=UserRole.student,
        email="fee@bb.edu.in",
    )
    db_session.add(user)
    db_session.flush()

    student = Student(
        user_id=user.id,
        enrollment_no="BB10001",
        first_name="Fee",
        last_name="Student",
        dob=date(2000, 1, 1),
        course_id=course.id,
        session_id=sess.id,
        admission_date=date(2024, 6, 1),
    )
    db_session.add(student)
    db_session.flush()

    # Create a fee record
    fee = Fee(
        student_id=student.id,
        session_id=sess.id,
        total_amount=50000.0,
        paid_amount=10000.0,
        due_date=date(2024, 8, 1),
        status=FeeStatus.partial,
    )
    db_session.add(fee)
    db_session.commit()
    return db_session, student, fee, sess


class TestFeeService:
    def test_get_student_fees(self, seeded_db):
        db, student, fee, sess = seeded_db
        service = FeeService(db)
        fees = service.get_student_fees(student.id)
        assert len(fees) == 1
        assert fees[0]["total_amount"] == 50000.0
        assert fees[0]["paid_amount"] == 10000.0

    def test_get_student_fees_empty(self, db_session):
        service = FeeService(db_session)
        fees = service.get_student_fees(999)
        assert fees == []

    def test_record_payment(self, seeded_db):
        db, student, fee, sess = seeded_db
        service = FeeService(db)
        receipt = service.record_payment(fee.id, 40000.0, "UPI", "txn_123")
        assert receipt is not None
        assert receipt.startswith("REC-")

        # Verify fee status changed to paid
        updated = db.query(Fee).filter(Fee.id == fee.id).first()
        assert updated.paid_amount == 50000.0
        assert updated.status == FeeStatus.paid

    def test_record_payment_partial(self, seeded_db):
        db, student, fee, sess = seeded_db
        service = FeeService(db)
        service.record_payment(fee.id, 5000.0, "Cash")
        updated = db.query(Fee).filter(Fee.id == fee.id).first()
        assert updated.paid_amount == 15000.0
        assert updated.status == FeeStatus.partial

    def test_record_payment_not_found(self, seeded_db):
        db, student, fee, sess = seeded_db
        service = FeeService(db)
        with pytest.raises(ValueError, match="Fee record not found"):
            service.record_payment(999, 1000.0, "Cash")

    def test_get_all_fees(self, seeded_db):
        db, student, fee, sess = seeded_db
        service = FeeService(db)
        all_fees = service.get_all_fees()
        assert len(all_fees) == 1

    def test_soft_deleted_fees_excluded(self, seeded_db):
        """Soft-deleted fees should not appear in queries."""
        db, student, fee, sess = seeded_db
        service = FeeService(db)

        # Soft-delete the fee
        fee.is_deleted = True
        db.commit()

        fees = service.get_all_fees()
        assert fees == []

        student_fees = service.get_student_fees(student.id)
        assert student_fees == []

    def test_soft_deleted_payment_rejected(self, seeded_db):
        """Recording payment against soft-deleted fee should raise error."""
        db, student, fee, sess = seeded_db
        service = FeeService(db)

        fee.is_deleted = True
        db.commit()

        with pytest.raises(ValueError, match="deleted"):
            service.record_payment(fee.id, 1000.0, "Cash")

    def test_payment_creates_fee_payment_record(self, seeded_db):
        db, student, fee, sess = seeded_db
        service = FeeService(db)
        service.record_payment(fee.id, 10000.0, "Bank Transfer")

        payments = db.query(FeePayment).filter(FeePayment.fee_id == fee.id).all()
        assert len(payments) == 1
        assert payments[0].amount == 10000.0
        assert payments[0].payment_mode == "Bank Transfer"
