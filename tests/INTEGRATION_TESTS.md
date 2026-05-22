# Integration Test Layer (Real DB + Redis)

This project now has a second backend test layer in `tests/integration/`.

## What this layer validates

- Real Postgres writes/reads through FastAPI auth endpoints.
- Real Redis state for refresh token lifecycle.
- Refresh token rotation and reuse detection.
- Real `/api/readyz` behavior with DB + Redis.

## Files

- `tests/integration/conftest.py`
- `tests/integration/test_auth_flow_integration.py`
- `docker-compose.integration.yml`
- `scripts/run_integration_tests.ps1`

## Why this is a second layer

- Unit/route tests (`tests/*.py`) are fast and isolated with mocks.
- Integration tests (`tests/integration/*.py`) hit real dependencies.
- This catches issues mocks cannot: schema mismatches, connection issues, Redis behavior.

## Run flow (step-by-step)

1. Start Docker Desktop.
2. In PowerShell, from repo root, run:

```powershell
./scripts/run_integration_tests.ps1
```

The script does:
- `docker compose -f docker-compose.integration.yml up -d`
- sets env vars for integration endpoints
- runs `pytest tests/integration -q`
- tears down containers with `docker compose ... down -v`

## Manual commands (if you prefer)

```powershell
docker compose -f docker-compose.integration.yml up -d
$env:RUN_INTEGRATION = "1"
$env:DATABASE_URL = "postgresql://gridpilot:gridpilot@127.0.0.1:5433/gridpilot_test"
$env:REDIS_URL = "redis://127.0.0.1:6380/0"
c:/Users/ASUS/projekte/react_1/GridPilot/app/venv/Scripts/python.exe -m pytest tests/integration -q
docker compose -f docker-compose.integration.yml down -v
```

## Default behavior

When `RUN_INTEGRATION` is not set to `1`, integration tests are skipped. This keeps normal CI and local runs fast.

## Troubleshooting

- If Docker command fails with daemon errors, Docker Desktop is not running correctly.
- If tests fail on connection refused, confirm ports 5433 and 6380 are free.
- If DB schema issues occur, rerun with clean containers (`down -v` then `up -d`).
