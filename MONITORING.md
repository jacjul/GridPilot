# Monitoring Stack (Senior Baseline)

This repository now includes a production-minded monitoring baseline:
- Prometheus with persistent TSDB and alert rules
- Alertmanager routing baseline
- Grafana with provisioned datasource and dashboard
- Postgres and Redis exporters for infrastructure metrics

## Services

Defined in docker compose:
- `prometheus` at `:9090`
- `alertmanager` at `:9093`
- `grafana` at `:3000`
- `postgres_exporter` on internal network
- `redis_exporter` on internal network

## Start (dev/local)

```powershell
docker compose --env-file .env.compose -f docker-compose.yml up -d
```

## Start (prod override)

```powershell
docker compose --env-file .env.compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

In production override, monitoring UIs are bound to localhost only:
- `127.0.0.1:3000` Grafana
- `127.0.0.1:9090` Prometheus
- `127.0.0.1:9093` Alertmanager

Use SSH tunnel to access remotely.

## Required env vars

Set in `.env.compose` for production:

```dotenv
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=change_me_strong
```

## Provisioning

Grafana auto-loads:
- Datasource: `monitoring/grafana/provisioning/datasources/prometheus.yml`
- Dashboard provider: `monitoring/grafana/provisioning/dashboards/dashboards.yml`
- Dashboard JSON: `monitoring/grafana/dashboards/gridpilot-overview.json`

## Alert rules

Prometheus rule file:
- `alert_rules.yml`

Current baseline alerts:
- API down
- Postgres exporter down
- Redis exporter down
- Missing API scrape target
- Prometheus config/TSDB reload issues

## Recommended next hardening

- Integrate Alertmanager receiver(s) (Slack, email, Opsgenie, PagerDuty).
- Add service-level SLO alerts (error rate, latency) once API metrics are stabilized.
- Add recording rules for expensive PromQL queries.
- Add backup for Grafana state and dashboards if edited through UI.
