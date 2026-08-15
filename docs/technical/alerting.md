# BB-IMS Alerting & Monitoring Guide

## Overview

The BB-IMS monitoring stack uses **Prometheus** for metrics collection and **Alertmanager** for alert routing and notification. This document describes the alerting rules, their thresholds and rationale, and how to configure notification channels.

## Alerting Rules

The canonical set of alerting rules is defined in `monitoring/alerts.yml`. Below is a summary of each rule:

| Rule Name | Expression | Threshold | Severity | Rationale |
| ----------- | ----------- | ----------- | ---------- | ----------- |
| `ApiErrorRateSpike` | 5xx rate / total request rate > 5% over 5m | > 5% | critical | Indicates server-side failures or code defects |
| `ExcessiveAuthFailures` | Failed login rate > 0.033 req/s (≈10/5min) | > 10 per 5m | warning | Signals brute-force attack |
| `DatabaseConnectionPoolExhaustion` | DB health gauge < 1 (unhealthy) | 1 failed check | critical | DB unreachable or pool exhausted |
| `CeleryTaskFailureRate` | Failed tasks / total tasks > 10% over 10m | > 10% | warning | Indicates worker or task issues |
| `HealthCheckFailure` | HTTP 503 on /health for > 1m | > 1 consecutive | critical | API unable to serve requests |

## Alertmanager Configuration

### Adding Alertmanager to Docker Compose

Add the following service to your `docker-compose.yml`:

```yaml
alertmanager:
  image: prom/alertmanager:v0.27.0
  container_name: bb_ims_alertmanager
  command:
    - '--config.file=/etc/alertmanager/alertmanager.yml'
    - '--storage.path=/alertmanager'
  volumes:
    - ./monitoring/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
    - alertmanager_data:/alertmanager
  ports:
    - "9093:9093"
  restart: unless-stopped
```

### Basic Alertmanager Config

Create `monitoring/alertmanager.yml`:

```yaml
route:
  receiver: 'default-receiver'
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

receivers:
  - name: 'default-receiver'
    # ── Placeholder: Replace with your notification channel ──
    # Supported receivers: slack, pagerduty, email, webhook, etc.
    # See https://prometheus.io/docs/alerting/latest/configuration/
    
    # Example: Slack
    # slack_configs:
    #   - api_url: '<your-slack-webhook-url>'  # e.g. https://hooks.slack.com/services/...
    #     channel: '#bb-ims-alerts'
    #     send_resolved: true
    #     title: '{{ .GroupLabels.alertname }}'
    #     text: '{{ .CommonAnnotations.description }}'

    # Example: Email
    # email_configs:
    #   - to: 'ops@bb-edu.in'
    #     from: 'alertmanager@bb-edu.in'
    #     smarthost: 'smtp.gmail.com:587'
    #     auth_username: 'alertmanager@bb-edu.in'
    #     auth_password: '<app-password>'

    # Example: PagerDuty
    # pagerduty_configs:
    #   - routing_key: '<your-pagerduty-integration-key>'
    #     severity: '{{ .CommonLabels.severity }}'

    # Fallback: Webhook for custom integrations
    webhook_configs:
      - url: 'http://localhost:8080/alert-hook'  # ← Replace with your webhook URL
        send_resolved: true

# Inhibit rules: suppress less-severe alerts when critical ones fire
inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname']
```

## Integration with Existing Prometheus

The existing Prometheus setup (defined in `docker-compose.yml`) already exposes a `/metrics` endpoint. To enable alerting:

1. **Mount the alerting rules** into your Prometheus container:
   ```yaml
   prometheus:
     image: prom/prometheus:v2.50.0
     volumes:
       - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
       - ./monitoring/alerts.yml:/etc/prometheus/alert.rules
     command:
       - '--config.file=/etc/prometheus/prometheus.yml'
   ```

2. **Update Prometheus config** (`monitoring/prometheus.yml`) to reference the rules file:
   ```yaml
   rule_files:
     - '/etc/prometheus/alert.rules'
   
   alerting:
     alertmanagers:
       - static_configs:
           - targets: ['alertmanager:9093']
   ```

## Testing Alert Rules

To verify that alert rules are syntactically valid:

```bash
# Using promtool (part of Prometheus distribution)
promtool check rules monitoring/alerts.yml

# To test against synthetic metrics, use the unit test feature:
promtool test rules monitoring/alerts_test.yml
```

### Manual Verification

You can trigger a health-check failure alert by stopping the database:

```bash
docker compose stop postgres
# Wait 1 minute — the HealthCheckFailure alert should fire
docker compose start postgres
```

## Notification Channels

The `alertmanager.yml` above uses a `webhook_configs` placeholder. Configure at least one real notification channel before relying on alerts in production:

| Channel | Setup Complexity | Best For |
| --------- | ----------------- | ---------- |
| Slack | Low (webhook URL) | Team collaboration |
| Email | Medium (SMTP config) | Auditable records |
| PagerDuty | Medium (integration key) | On-call rotations |
| Custom Webhook | High (implement endpoint) | Custom integrations |

## Alertmanager Dashboard

Alertmanager exposes a web UI on port **9093** (default). Access it at:

```
http://<your-server>:9093
```

The UI shows all active, silenced, and inhibited alerts. You can also silence alerts directly from the UI.
