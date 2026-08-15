"""Timetable service — manages course schedules and auto-generation."""

from datetime import time

from sqlalchemy.orm import Session

from database.models import Subject, Timetable


class TimetableService:
    def __init__(self, db: Session):
        self.db = db

    def get_timetable_for_course(self, course_id: int):
        """Return all timetable entries for a given course, ordered by day then time."""
        entries = (
            self.db.query(Timetable)
            .filter(Timetable.course_id == course_id)
            .order_by(
                Timetable.day_of_week.asc(),
                Timetable.start_time.asc(),
            )
            .all()
        )
        return [self._format_entry(e) for e in entries]

    def get_all_course_timetables(self):
        """Group timetable entries by course for display."""
        entries = (
            self.db.query(Timetable)
            .order_by(Timetable.course_id, Timetable.day_of_week, Timetable.start_time)
            .all()
        )
        grouped = {}
        for e in entries:
            course_name = e.course.name if e.course else f"Course #{e.course_id}"
            if course_name not in grouped:
                grouped[course_name] = []
            grouped[course_name].append(self._format_entry(e))
        return grouped

    def auto_generate(self, course_id: int, days: list[str] = None) -> dict:
        """Auto-generate a timetable for a course by distributing subjects across weekdays.

        Args:
            course_id: The course to generate a timetable for.
            days: List of weekday names to use (defaults to Mon-Fri).

        Returns:
            dict with keys:
                - status: "created" | "skipped" | "error"
                - message: Human-readable summary
                - entries: List of created timetable entries (or empty)
        """
        if days is None:
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

        # Get subjects for this course that have a staff member assigned
        subjects = (
            self.db.query(Subject)
            .filter(Subject.course_id == course_id, Subject.staff_id.isnot(None))
            .all()
        )

        if not subjects:
            # Try to get all subjects even without staff
            subjects = self.db.query(Subject).filter(Subject.course_id == course_id).all()
            if not subjects:
                return {
                    "status": "skipped",
                    "message": "No subjects found for this course. Add subjects first.",
                    "entries": [],
                }

        # Clear existing timetable for this course to avoid duplicates
        self.db.query(Timetable).filter(Timetable.course_id == course_id).delete()
        self.db.flush()

        # Time slots: 9:00-9:55, 10:00-10:55, 11:00-11:55, 12:00-12:55, 14:00-14:55, 15:00-15:55
        time_slots = [
            (time(9, 0), time(9, 55)),
            (time(10, 0), time(10, 55)),
            (time(11, 0), time(11, 55)),
            (time(12, 0), time(12, 55)),
            (time(14, 0), time(14, 55)),
            (time(15, 0), time(15, 55)),
        ]

        created_entries = []
        # Distribute subjects across available days and time slots
        for idx, subject in enumerate(subjects):
            day_idx = idx % len(days)
            slot_idx = (idx // len(days)) % len(time_slots)
            day = days[day_idx]
            start_time, end_time = time_slots[slot_idx]

            # Pick a generic room number based on course and slot
            room_no = f"Room {101 + (slot_idx % 6)}"

            # If subject has no staff assigned, skip it rather than using a placeholder
            if not subject.staff_id:
                continue

            entry = Timetable(
                course_id=course_id,
                subject_id=subject.id,
                staff_id=subject.staff_id,
                day_of_week=day,
                start_time=start_time,
                end_time=end_time,
                room_no=room_no,
            )
            self.db.add(entry)
            created_entries.append(entry)

        # If all subjects were skipped (no staff assigned), return early
        if not created_entries:
            # Rollback the delete since we couldn't create anything
            self.db.rollback()
            return {
                "status": "skipped",
                "message": "No subjects have staff assigned. Assign faculty to subjects first, then retry.",
                "entries": [],
            }

        self.db.commit()

        # Build formatted result from the local objects (still tracked by SQLAlchemy)
        result_entries = []
        for e in created_entries:
            # Manually resolve relationships since we're still in the same session
            subject_name = e.subject.name if e.subject else f"Subject #{e.subject_id}"
            staff_name = f"{e.staff.first_name} {e.staff.last_name}" if e.staff else "Unassigned"
            course_name = e.course.name if e.course else f"Course #{e.course_id}"
            result_entries.append(
                {
                    "id": e.id,
                    "course_id": e.course_id,
                    "course_name": course_name,
                    "subject_id": e.subject_id,
                    "subject_name": subject_name,
                    "staff_id": e.staff_id,
                    "staff_name": staff_name,
                    "day_of_week": e.day_of_week,
                    "start_time": e.start_time.strftime("%H:%M"),
                    "end_time": e.end_time.strftime("%H:%M"),
                    "room_no": e.room_no or "TBD",
                }
            )

        return {
            "status": "created",
            "message": f"Generated {len(result_entries)} timetable entries across {len(days)} days.",
            "entries": result_entries,
        }

    def _format_entry(self, entry):
        if not entry:
            return None
        return {
            "id": entry.id,
            "course_id": entry.course_id,
            "course_name": entry.course.name if entry.course else f"Course #{entry.course_id}",
            "subject_id": entry.subject_id,
            "subject_name": entry.subject.name if entry.subject else f"Subject #{entry.subject_id}",
            "staff_id": entry.staff_id,
            "staff_name": (
                f"{entry.staff.first_name} {entry.staff.last_name}" if entry.staff else "Unassigned"
            ),
            "day_of_week": entry.day_of_week,
            "start_time": entry.start_time.strftime("%H:%M"),
            "end_time": entry.end_time.strftime("%H:%M"),
            "room_no": entry.room_no or "TBD",
        }
