# HTTPS deployment with edge Nginx

This setup makes Nginx the TLS entrypoint:
- `edge` handles public `80/443`
- `frontend` and `api` stay internal to Docker network

## 1) Put TLS cert files in project

Create a folder named `certs` in project root and add:
- `certs/fullchain.pem`
- `certs/privkey.pem`

## 2) Start stack

```bash
docker compose --env-file .env.compose up -d --build
```

## 3) Verify

```bash
docker compose --env-file .env.compose ps
```

You should see:
- `gridpilot_edge` exposing `80` and `443`
- `gridpilot_api` no public host port
- `gridpilot_frontend` no public host port

## 4) Access app

- HTTP redirects to HTTPS automatically
- Use `https://<your-domain-or-host>`

## Notes

- For local testing with self-signed certs, browsers will show a warning unless cert is trusted.
- For production, use valid certificates (for example Let's Encrypt).
