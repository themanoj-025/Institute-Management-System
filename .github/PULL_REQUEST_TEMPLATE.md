## Description

Please include a summary of the changes and the related issue. What problem does this PR solve?

Fixes # (issue)

## Type of Change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] New module or service
- [ ] UI/UX enhancement (GUI, Web, or CLI)
- [ ] Documentation update
- [ ] Refactoring / code cleanup
- [ ] Code quality (linting, type checking, security)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)

## Modules Affected

- [ ] Student management
- [ ] Staff management
- [ ] Course management
- [ ] Attendance tracking
- [ ] Fee management
- [ ] Results / grades
- [ ] Placement / career services
- [ ] Feedback / surveys
- [ ] Analytics / reports
- [ ] Authentication / roles
- [ ] Notifications
- [ ] Export (PDF, Excel, CSV)
- [ ] Search

## Testing

- [ ] `SECRET_KEY=test-key python -m pytest tests/ -v` — all existing tests pass
- [ ] `mypy . --ignore-missing-imports` — type checks pass (if applicable)
- [ ] Tested with GUI (`python main.py`)
- [ ] Tested with Web interface (`uvicorn api.main:app --port 8000`)
- [ ] Migration tested (`cd database && SECRET_KEY=test-key python -m alembic -c alembic.ini upgrade head`)
- [ ] Migration downgrade tested (`alembic downgrade -1`)
- [ ] ML promotion history endpoint: `GET /v1/admin/ml/promotion-history` returns valid data
- [ ] No `datetime.now(timezone.utc)` calls added outside `utils/time.py` (use `utc_now()` instead)

## Checklist

- [ ] My code follows the existing project conventions and style
- [ ] `black` and `isort` have been run on my changes
- [ ] I have updated documentation if needed
- [ ] I have added or updated environment variables if needed
- [ ] My changes do not introduce new warnings or errors
- [ ] I have considered security implications (see `SECURITY.md`)
- [ ] I have tested all affected interfaces

## Additional Context

Add any other context about the PR here, such as database migration notes.
