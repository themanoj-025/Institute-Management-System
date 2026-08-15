"""Fee service with soft-delete filtering.

All queries against Fee/FeePayment filter ``is_deleted == False``
by default, so soft-deleted records are excluded from normal operations.
"""

import uuid

from sqlalchemy.orm import Session

from database.models import Fee, FeePayment, FeeStatus


class FeeService:
    def __init__(self, db: Session):
        self.db = db

    def get_student_fees(self, student_id):
        fees = (
            self.db.query(Fee).filter(Fee.student_id == student_id, Fee.is_deleted == False).all()
        )
        return [self._format_fee(f) for f in fees]

    def record_payment(self, fee_id, amount, mode, transaction_id=None):
        fee = self.db.query(Fee).filter(Fee.id == fee_id, Fee.is_deleted == False).first()
        if not fee:
            raise ValueError("Fee record not found or has been deleted")

        receipt_no = f"REC-{uuid.uuid4().hex[:8].upper()}"
        payment = FeePayment(
            fee_id=fee_id,
            amount=amount,
            payment_mode=mode,
            transaction_id=transaction_id,
            receipt_no=receipt_no,
        )
        self.db.add(payment)

        fee.paid_amount += amount
        if fee.paid_amount >= fee.total_amount:
            fee.status = FeeStatus.paid
        else:
            fee.status = FeeStatus.partial

        self.db.commit()
        return receipt_no

    def get_all_fees(self):
        fees = self.db.query(Fee).filter(Fee.is_deleted == False).order_by(Fee.id.desc()).all()
        return [self._format_fee(f) for f in fees]

    def _format_fee(self, fee):
        student_name = (
            f"{fee.student.first_name} {fee.student.last_name}" if fee.student else "Unknown"
        )
        return {
            "id": fee.id,
            "student_name": student_name,
            "total_amount": fee.total_amount,
            "paid_amount": fee.paid_amount,
            "balance": fee.total_amount
            - fee.paid_amount
            - fee.scholarship_amount
            + fee.fine_amount,
            "due_date": fee.due_date.isoformat() if fee.due_date else None,
            "status": fee.status.value,
            "scholarship_amount": fee.scholarship_amount,
            "fine_amount": fee.fine_amount,
        }
