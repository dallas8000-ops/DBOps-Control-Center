# DBOps observability (Growth-tier production)

Minimal Prometheus + Grafana setup for single-region Render or AWS deployments.

## What is included

| Component | Location |
|-----------|----------|
| Prometheus metrics | `GET /metrics` on **dbops-api** |
| Observability health | `GET /health/observability` |
| Grafana dashboard template | [`grafana-dbops-dashboard.json`](./grafana-dbops-dashboard.json) |
| Example scrape config | [`prometheus-scrape.example.yml`](./prometheus-scrape.example.yml) |

Metrics exposed:

- `dbops_http_requests_total{method,route,status_class}`
- `dbops_http_request_duration_seconds{method,route}`

Disable metrics with `METRICS_ENABLED=0` if your platform scrapes health only.

## Quick start

1. Deploy **dbops-api** with `METRICS_ENABLED=1` (default).
2. Point Prometheus at `https://your-api.example.com/metrics`.
3. Import `grafana-dbops-dashboard.json` into Grafana.
4. Optional: set `REDIS_URL` so rate limits are shared across API replicas (`GET /health/observability` reports `rate_limit_backend`).

## Render note

Render does not run Prometheus for you. Use Grafana Cloud free tier, self-hosted Prometheus, or Datadog/OpenTelemetry collector scraping `/metrics`.

## Alerts (recommended)

- 5xx rate > 1% for 5 minutes (`status_class="5xx"`)
- p95 latency > 2s on `/reports/run` or `/incidents`
- `GET /health` or `GET /health/scheduler` failing

See [`../INCIDENT_RESPONSE.md`](../INCIDENT_RESPONSE.md) for billing and SMTP triage.
