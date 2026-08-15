from sqlalchemy.orm import Session

from database.models import Feedback
from utils.time import utc_now


class FeedbackService:
    def __init__(self, db: Session):
        self.db = db

    def submit_feedback(self, user_id, category, message):
        feedback = Feedback(user_id=user_id, category=category, message=message)
        self.db.add(feedback)
        self.db.commit()
        return self._format_feedback(feedback)

    def get_user_feedback(self, user_id):
        feedbacks = (
            self.db.query(Feedback)
            .filter(Feedback.user_id == user_id)
            .order_by(Feedback.id.desc())
            .all()
        )
        return [self._format_feedback(f) for f in feedbacks]

    def get_all_feedback(self):
        feedbacks = self.db.query(Feedback).order_by(Feedback.id.desc()).all()
        return [self._format_feedback(f) for f in feedbacks]

    def reply_to_feedback(self, feedback_id, replier_id, reply_text):
        feedback = self.db.query(Feedback).filter(Feedback.id == feedback_id).first()
        if not feedback:
            return None
        feedback.reply = reply_text
        feedback.replied_by = replier_id
        feedback.replied_on = utc_now()
        self.db.commit()
        return self._format_feedback(feedback)

    def _format_feedback(self, feedback):
        return {
            "id": feedback.id,
            "category": feedback.category,
            "message": feedback.message,
            "submitted_on": feedback.submitted_on.isoformat(),
            "reply": feedback.reply,
            "replied_on": feedback.replied_on.isoformat() if feedback.replied_on else None,
            "user": feedback.user.username if feedback.user else "Unknown",
        }
