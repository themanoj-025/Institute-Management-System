from sqlalchemy.orm import Session

from database.models import Notice


from typing import Optional


class NoticeService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all_notices(self, target_role: str | None = None) -> list[dict]:
        query = self.db.query(Notice)
        if target_role:
            query = query.filter(Notice.target_role.in_(["all", target_role]))

        notices = query.order_by(Notice.is_pinned.desc(), Notice.id.desc()).all()
        return [self._format_notice(n) for n in notices]

    def create_notice(self, title: str, content: str, author_id: int, target_role: str = "all", is_pinned: bool = False) -> dict:
        notice = Notice(
            title=title,
            content=content,
            author_id=author_id,
            target_role=target_role,
            is_pinned=is_pinned,
        )
        self.db.add(notice)
        self.db.commit()
        return self._format_notice(notice)

    def delete_notice(self, notice_id: int) -> bool:
        notice = self.db.query(Notice).filter(Notice.id == notice_id).first()
        if notice:
            self.db.delete(notice)
            self.db.commit()
        return True

    def _format_notice(self, notice: Notice) -> dict:
        return {
            "id": notice.id,
            "title": notice.title,
            "content": notice.content,
            "author": notice.author.username if notice.author else "Unknown",
            "date": notice.created_at.strftime("%d %b %Y"),
            "target_role": notice.target_role,
            "is_pinned": notice.is_pinned,
        }
