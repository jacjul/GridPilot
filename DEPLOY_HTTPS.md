# HTTPS deployment with edge Nginx (build on VPS, no CI/CD)

This guide matches the current production setup:
- [docker-compose.yml](docker-compose.yml): base services
- [docker-compose.prod.yml](docker-compose.prod.yml): production overrides (API not exposed, edge exposes 80/443)
- [nginx.edge.conf](nginx.edge.conf): TLS edge proxy for frontend and API

Architecture:
- edge handles public 80/443
- api and frontend stay internal in Docker network

## 1) Prepare project on VPS

Run these on your Ubuntu VPS in the project directory.

	cd /opt/gridpilot
	git pull

## 2) Configure production environment

Create or update .env.compose:

	POSTGRES_DB=gridpilot
	POSTGRES_USER=gridpilot
	POSTGRES_PASSWORD=CHANGE_ME_STRONG

	ENV=prod
	DATABASE_URL=postgresql+psycopg2://gridpilot:CHANGE_ME_URL_ENCODED@postgres:5432/gridpilot
	REDIS_URL_AUTH=redis://redis:6379/0
	REDIS_URL_CELERY=redis://redis:6379/1
	SECRET_KEY=CHANGE_ME_LONG_RANDOM_SECRET
	ALGORITHM=HS256
	ACCESS_TOKEN_MIN=15
	REFRESH_TOKEN_DAYS=7
	SECURE_COOKIE=true
	SAMESITE_COOKIE=lax

Important:
- Use a strong password and secret key.
- If password includes reserved URL characters (@ : / # ? &), URL-encode it in DATABASE_URL.

## 3) Provide TLS certificate files for edge Nginx

The edge container expects:
- certs/fullchain.pem
- certs/privkey.pem

If certs already exist on host:

	mkdir -p certs
	cp /path/to/fullchain.pem certs/fullchain.pem
	cp /path/to/privkey.pem certs/privkey.pem
	chmod 600 certs/privkey.pem

If you use Let's Encrypt on host:

	sudo certbot certonly --standalone -d your-domain.com -d www.your-domain.com --agree-tos -m you@example.com --non-interactive
	mkdir -p certs
	sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem certs/fullchain.pem
	sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem certs/privkey.pem
	sudo chown $USER:$USER certs/fullchain.pem certs/privkey.pem
	chmod 600 certs/privkey.pem

## 4) Start the production stack

	docker compose --env-file .env.compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d

## 5) Run database migrations (required on first deploy)

	docker compose --env-file .env.compose -f docker-compose.yml -f docker-compose.prod.yml run --rm api alembic -c app/alembic.ini upgrade head

## 6) Verify containers and endpoints

	docker compose --env-file .env.compose -f docker-compose.yml -f docker-compose.prod.yml ps
	docker compose --env-file .env.compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=200 edge api
	curl -I https://your-domain.com
	curl -I https://your-domain.com/api/healthz

Expected:
- edge publishes 80/443
- api has no published host port
- frontend has no published host port
- health endpoint returns success

## 7) Configure certificate renewal hook (recommended)

If certbot renews certificates on host, copy renewed files into project certs and restart edge.

	sudo tee /etc/letsencrypt/renewal-hooks/deploy/gridpilot-reload.sh > /dev/null << 'EOF'
	#!/usr/bin/env bash
	set -euo pipefail
	DOMAIN="your-domain.com"
	PROJECT_DIR="/opt/gridpilot"
	cp /etc/letsencrypt/live/${DOMAIN}/fullchain.pem ${PROJECT_DIR}/certs/fullchain.pem
	cp /etc/letsencrypt/live/${DOMAIN}/privkey.pem ${PROJECT_DIR}/certs/privkey.pem
	chmod 600 ${PROJECT_DIR}/certs/privkey.pem
	cd ${PROJECT_DIR}
	docker compose --env-file .env.compose -f docker-compose.yml -f docker-compose.prod.yml restart edge
	EOF
	sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/gridpilot-reload.sh

Test renewal:

	sudo certbot renew --dry-run

## 8) Update deployment (next releases)

	cd /opt/gridpilot
	git pull
	docker compose --env-file .env.compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
	docker compose --env-file .env.compose -f docker-compose.yml -f docker-compose.prod.yml run --rm api alembic -c app/alembic.ini upgrade head

## Notes

- Do not commit .env.compose to git.
- Keep ports 80 and 443 open in UFW; keep direct database and redis ports closed.
- BASE_URL_API in .env.compose is not used by current frontend code and can be removed.
