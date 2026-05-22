$ErrorActionPreference = "Stop"

$python = "c:/Users/ASUS/projekte/react_1/GridPilot/app/venv/Scripts/python.exe"

Write-Host "Checking Docker daemon..."
docker info | Out-Null

Write-Host "Starting integration dependencies (Postgres + Redis)..."
docker compose -f docker-compose.integration.yml up -d --wait

try {
    $env:RUN_INTEGRATION = "1"
    $env:DATABASE_URL = "postgresql://gridpilot:gridpilot@127.0.0.1:5433/gridpilot_test"
    $env:REDIS_URL = "redis://127.0.0.1:6380/0"

    Write-Host "Running integration test layer..."
    & $python -m pytest tests/integration -q
}
finally {
    Write-Host "Stopping integration dependencies..."
    docker compose -f docker-compose.integration.yml down -v
}
