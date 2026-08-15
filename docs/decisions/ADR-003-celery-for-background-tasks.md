# ADR-003: Celery for Background Task Processing

**Status**: Accepted
**Date**: 2026-07-24 (updated 2026-07-25)
**Author**: Architecture Team

## Context

The original system ran all operations synchronously in the request thread. This caused:
- API endpoints blocked during email sending (SMTP handshake takes 1-5 seconds)
- Report generation timed out on large datasets (>1000 students)
- Model retraining blocked the dashboard until training completed
- No retry mechanism for failed operations (email, exports)
- No periodic cleanup for expired OTP codes or revoked tokens

## Decision

Use **Celery** with **Redis** as the message broker for background task processing.

## Rationale

### Why Celery over bare threading

| Factor | Celery + Redis | Bare `threading.Thread` | APScheduler |
| -------- | --------------- | ------------------------ | ------------- |
| **Persistence** | Tasks survive worker restart (Redis) | Lost on crash | In-memory |
| **Retries** | Built-in with backoff | Manual implementation | Manual |
| **Scheduling** | Celery Beat (cron-style) | Manual timer threads | Native |
| **Scaling** | N workers across processes/containers | Single process only | Single process |
| **Monitoring** | Flower dashboard, task tracking | No visibility | No visibility |
| **Failure handling** | Configurable retries, ack-late | Caller must catch | Caller must catch |
| **Docker support** | Separate worker container | In-app threads | In-app threads |

### Task inventory

| Task | Trigger | Retries | Description |
| ------ | --------- | --------- | ------------- |
| `send_email_task` | On-demand (OTP) | 3 (60s backoff) | Send SMTP email |
| `retrain_ml_model_task` | Weekly (Celery Beat) | 3 (10min backoff) | Retrain XGBoost; run promotion gate; check post-retrain drift |
| `check_ml_drift_task` | Daily (Celery Beat) | 1 | Compare current features vs. reference; store results in SystemConfig |
| `cleanup_expired_otps_task` | Hourly (Celery Beat) | 2 | Delete expired OTP codes from table |
| `cleanup_revoked_tokens_task` | Daily (Celery Beat) | 2 | Delete expired blacklist entries |
| `generate_export_task` | On-demand (export) | 2 | Large export generation (CSV, Excel, PDF) |

### Retry policy

```python
task_acks_late = True          # Don't ack until task completes
task_reject_on_worker_lost = True  # Requeue if worker dies
task_default_retry_delay = 60      # 60s before first retry
task_max_retries = 3               # Max 3 retries
```

### Drift Detection Flow

The `check_ml_drift_task` runs daily and:
1. Computes current feature distributions from the database
2. Compares them against the reference distributions saved at training time
   using PSI (Population Stability Index)
3. Stores drift metrics in `SystemConfig` for admin dashboard visibility
4. Flags features as drifted if PSI > 0.10; flags severe drift if PSI > 0.25

The post-retrain path also runs drift detection to establish a new baseline.

## Consequences

- **Redis required**: Added as `redis` dependency and Docker service
- **Worker container**: Separate `Dockerfile.worker` with Celery entrypoint
- **Celery Beat**: Periodic task scheduler runs in the worker
- **Email sending**: Moved from blocking in-thread to async Celery task
- **ML retraining**: Scheduled weekly; only promotes model if metrics meet/exceed current
- **Drift monitoring**: Daily check; results visible in admin dashboard

## Related

- `celery_app.py` — Celery application and task definitions
- `Dockerfile.worker` — Worker image
- `docker-compose.yml` — Redis + worker services
- `ml/drift.py` — PSI-based drift detection
- ADR-001: PostgreSQL as production database
- ADR-005: ML Model Promotion Gate
