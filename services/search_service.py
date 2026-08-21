"""Global search service with FTS5 and LIKE fallback.

Uses parameterized queries throughout (no raw f-string SQL injection risk).
Silent `except: pass` blocks have been replaced with proper logged exception handling.
"""

import threading

from sqlalchemy import event, or_, text
from sqlalchemy.orm import Session

from database.models import Course, Notice, Staff, Student, Subject
from utils.logger import setup_logger

logger = setup_logger("search", context={"service": "search", "version": "1.0"})


class SearchService:
    def __init__(self, db: Session) -> None:
        self.db = db
        try:
            self._init_fts()
        except Exception as exc:
            logger.warning("FTS5 init failed (SQLite may lack FTS5 support): %s", exc)

    def _init_fts(self) -> None:
        """Create FTS5 virtual tables if they don't exist."""
        self.db.execute(
            text(
                """
            CREATE VIRTUAL TABLE IF NOT EXISTS students_fts USING fts5(
                name, roll_no, email, content='students', content_rowid='id'
            );
        """
            )
        )
        self.db.execute(
            text(
                """
            CREATE VIRTUAL TABLE IF NOT EXISTS notices_fts USING fts5(
                title, body, content='notices', content_rowid='id'
            );
        """
            )
        )
        self.db.commit()
        logger.debug("FTS5 virtual tables initialised")

    def global_search(self, query: str, limit: int = 20) -> dict[str, list[dict[str, str | int]]]:
        if not query or len(query) < 2:
            return {}

        results = {
            "students": [],
            "staff": [],
            "courses": [],
            "notices": [],
            "subjects": [],
        }
        errors = []

        # Multi-threaded category queries
        def query_students() -> None:
            try:
                fts_query = self.db.execute(
                    text("SELECT rowid FROM students_fts WHERE students_fts MATCH :q LIMIT :lim"),
                    {"q": f"{query}*", "lim": limit},
                ).fetchall()

                if fts_query:
                    ids = [r[0] for r in fts_query]
                    matches = self.db.query(Student).filter(Student.id.in_(ids)).all()
                else:
                    matches = (
                        self.db.query(Student)
                        .filter(
                            or_(
                                Student.first_name.ilike(f"%{query}%"),
                                Student.last_name.ilike(f"%{query}%"),
                                Student.enrollment_no.ilike(f"%{query}%"),
                            )
                        )
                        .limit(limit)
                        .all()
                    )

                for s in matches:
                    results["students"].append(
                        {
                            "id": s.id,
                            "title": f"{s.first_name} {s.last_name}",
                            "subtitle": f"Roll No: {s.enrollment_no}",
                            "route": "manage_students",
                        }
                    )
            except Exception as exc:
                logger.error("Student search failed: %s", exc)
                errors.append(("students", str(exc)))

        def query_staff() -> None:
            try:
                matches = (
                    self.db.query(Staff)
                    .filter(
                        or_(
                            Staff.first_name.ilike(f"%{query}%"),
                            Staff.last_name.ilike(f"%{query}%"),
                            Staff.department.ilike(f"%{query}%"),
                        )
                    )
                    .limit(limit)
                    .all()
                )
                for s in matches:
                    results["staff"].append(
                        {
                            "id": s.id,
                            "title": f"{s.first_name} {s.last_name}",
                            "subtitle": f"Dept: {s.department} | {s.designation}",
                            "route": "manage_staff",
                        }
                    )
            except Exception as exc:
                logger.error("Staff search failed: %s", exc)
                errors.append(("staff", str(exc)))

        def query_courses() -> None:
            try:
                matches = (
                    self.db.query(Course)
                    .filter(
                        or_(
                            Course.name.ilike(f"%{query}%"),
                            Course.code.ilike(f"%{query}%"),
                            Course.description.ilike(f"%{query}%"),
                        )
                    )
                    .limit(limit)
                    .all()
                )
                for c in matches:
                    results["courses"].append(
                        {
                            "id": c.id,
                            "title": c.name,
                            "subtitle": f"Code: {c.code}",
                            "route": "manage_courses",
                        }
                    )
            except Exception as exc:
                logger.error("Course search failed: %s", exc)
                errors.append(("courses", str(exc)))

        def query_notices() -> None:
            try:
                fts_query = self.db.execute(
                    text("SELECT rowid FROM notices_fts WHERE notices_fts MATCH :q LIMIT :lim"),
                    {"q": f"{query}*", "lim": limit},
                ).fetchall()
                if fts_query:
                    ids = [r[0] for r in fts_query]
                    matches = self.db.query(Notice).filter(Notice.id.in_(ids)).all()
                else:
                    matches = (
                        self.db.query(Notice)
                        .filter(
                            or_(
                                Notice.title.ilike(f"%{query}%"),
                                Notice.content.ilike(f"%{query}%"),
                            )
                        )
                        .limit(limit)
                        .all()
                    )
                for n in matches:
                    results["notices"].append(
                        {
                            "id": n.id,
                            "title": n.title,
                            "subtitle": f"Target: {n.target_role}",
                            "route": "notice_board",
                        }
                    )
            except Exception as exc:
                logger.error("Notice search failed: %s", exc)
                errors.append(("notices", str(exc)))

        def query_subjects() -> None:
            try:
                matches = (
                    self.db.query(Subject)
                    .filter(
                        or_(
                            Subject.name.ilike(f"%{query}%"),
                            Subject.code.ilike(f"%{query}%"),
                        )
                    )
                    .limit(limit)
                    .all()
                )
                for s in matches:
                    results["subjects"].append(
                        {
                            "id": s.id,
                            "title": s.name,
                            "subtitle": f"Code: {s.code}",
                            "route": "manage_subjects",
                        }
                    )
            except Exception as exc:
                logger.error("Subject search failed: %s", exc)
                errors.append(("subjects", str(exc)))

        threads = [
            threading.Thread(target=query_students),
            threading.Thread(target=query_staff),
            threading.Thread(target=query_courses),
            threading.Thread(target=query_notices),
            threading.Thread(target=query_subjects),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        if errors:
            logger.warning("Search completed with %d errors: %s", len(errors), errors)

        return results


# Set up automatic FTS5 synchronizations
@event.listens_for(Student, "after_insert")
def sync_student_fts_insert(mapper, connection, target) -> None:
    try:
        connection.execute(
            text("INSERT INTO students_fts(rowid, name, roll_no) VALUES (:id, :name, :roll)"),
            {
                "id": target.id,
                "name": f"{target.first_name} {target.last_name}",
                "roll": target.enrollment_no,
            },
        )
    except Exception as exc:
        logger.error("FTS sync failed for student %d: %s", target.id, exc)


@event.listens_for(Notice, "after_insert")
def sync_notice_fts_insert(mapper, connection, target) -> None:
    try:
        connection.execute(
            text("INSERT INTO notices_fts(rowid, title, body) VALUES (:id, :title, :body)"),
            {"id": target.id, "title": target.title, "body": target.content},
        )
    except Exception as exc:
        logger.error("FTS sync failed for notice %d: %s", target.id, exc)
