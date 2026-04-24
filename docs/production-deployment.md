# Production Deployment README

This document describes the production deployment flow for this repository after cloning it from GitHub onto a public Linux server.

The production stack included in this repository is built around:

- `reverse-proxy`: public Nginx entrypoint on port `80`, with `443` added by a TLS compose override when built-in TLS is enabled
- `frontend`: internal static frontend container
- `backend`: internal FastAPI container
- `db`: internal MySQL container

Only the reverse proxy is exposed to the internet. The backend and database remain on the private Docker network.

## Files Added for Production

- [docker-compose.prod.yml](/Users/azure/ECG-Diagnosis-Suite/docker-compose.prod.yml)
- [docker-compose.prod.tls.yml](/Users/azure/ECG-Diagnosis-Suite/docker-compose.prod.tls.yml)
- [.env.production.example](/Users/azure/ECG-Diagnosis-Suite/.env.production.example)
- [scripts/deploy-production.sh](/Users/azure/ECG-Diagnosis-Suite/scripts/deploy-production.sh)
- [deploy/nginx/prod.conf.template](/Users/azure/ECG-Diagnosis-Suite/deploy/nginx/prod.conf.template)

## 1. Server Requirements

- Ubuntu 22.04 or another modern Linux distribution
- Docker Engine
- Docker Compose plugin
- At least 2 CPU / 4 GB RAM recommended
- At least 20 GB free disk space
- A public IP
- A domain name strongly recommended

## 2. Network and Firewall

Before deployment, open only the ports below on your cloud firewall / security group:

- `22/tcp` for SSH
- `80/tcp` for HTTP
- `443/tcp` for HTTPS only if `ENABLE_TLS=True`

Do not open:

- `3306`
- `8000`

The production compose file does not expose MySQL or FastAPI to the public internet.

## 3. Install Docker

If Docker is not installed yet:

```bash
curl -fsSL https://get.docker.com | sh
sudo systemctl enable docker
sudo systemctl start docker
docker --version
docker compose version
```

## 4. Clone the Repository

```bash
git clone https://github.com/suizhaoqinggong/ECG-Diagnosis-Suite.git
cd ECG-Diagnosis-Suite
```

If this is your own fork, use your own repository URL instead.

## 5. Prepare Production Environment Variables

Create the production environment file:

```bash
cp .env.production.example .env.production
```

Then edit it:

```bash
vim .env.production
```

You must change at least the following values:

- `APP_DOMAIN`
- `BACKEND_SECRET_KEY`
- `MYSQL_PASSWORD`
- `MYSQL_ROOT_PASSWORD`
- `BACKEND_CORS_ORIGINS`
- `BACKEND_ALLOWED_HOSTS`

Recommended values:

```env
APP_DOMAIN=ecg.your-domain.com
CLIENT_MAX_BODY_SIZE=20m

BACKEND_DEBUG=False
BACKEND_SECRET_KEY=replace-with-a-long-random-secret
BACKEND_API_DOCS_ENABLED=False
BACKEND_DEVICE=cpu
BACKEND_CONFIDENCE_THRESHOLD=0.7
BACKEND_MODEL_CHECKPOINT_PATH=models/checkpoints/best.ckpt
BACKEND_CORS_ORIGINS=["https://ecg.your-domain.com"]
BACKEND_ALLOWED_HOSTS=["ecg.your-domain.com"]

MYSQL_DATABASE=ecg_db
MYSQL_USER=ecg
MYSQL_PASSWORD=replace-with-a-strong-db-password
MYSQL_ROOT_PASSWORD=replace-with-a-different-root-password
```

Generate strong secrets on the server if needed:

```bash
openssl rand -hex 32
```

## 6. Prepare Model Files

Place your ECG model checkpoint in one of these paths:

- `models/checkpoints/best.ckpt`
- `models/weights/best.ckpt`

Example:

```bash
mkdir -p models/checkpoints
cp /path/to/your/best.ckpt models/checkpoints/best.ckpt
```

Production startup requires a real checkpoint. If no checkpoint exists in one of the supported paths, the backend exits with a startup error.

## 7. Deploy

Run the deployment script:

```bash
bash deploy.sh
```

This script will:

- create required runtime directories
- build the frontend and backend images
- start MySQL
- wait for the database health check
- run `alembic upgrade head`
- start FastAPI
- start the internal frontend container
- start the public Nginx reverse proxy

## 8. Verify the Deployment

If `ENABLE_TLS=True`, append `-f docker-compose.prod.tls.yml` to the Docker Compose commands in this section and the next one.

Check container status:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml ps
```

Check logs:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f
```

Health check:

```bash
curl http://127.0.0.1/health
```

If your domain already points to the server:

```bash
curl http://your-domain.com/health
```

If built-in TLS is enabled:

```bash
curl https://your-domain.com/health
```

Open in the browser:

- `http://your-domain.com/`

By default, API docs are disabled in production. If you intentionally enable them, they will be available at:

- `http://your-domain.com/docs`

## 9. Update an Existing Deployment

When you update code on the server:

```bash
git pull
bash deploy.sh
```

That rebuilds and restarts the production stack with the current repository state.

## 10. Common Operations

View logs:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f reverse-proxy
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f backend
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f frontend
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f db
```

Restart everything:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml restart
```

Stop everything:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml down
```

Rebuild from scratch:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml down
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

## 11. DNS Setup

Point your domain's `A` record to the server public IP:

- `ecg.your-domain.com -> <your-server-ip>`

Then make sure `.env.production` matches:

- `APP_DOMAIN=ecg.your-domain.com`
- `BACKEND_CORS_ORIGINS=["https://ecg.your-domain.com"]`
- `BACKEND_ALLOWED_HOSTS=["ecg.your-domain.com"]`

## 12. HTTPS

The production stack now supports optional built-in TLS termination.

To enable it:

1. Place your certificate and private key in `deploy/certs/`
2. Set these values in `.env.production`:

```env
ENABLE_TLS=True
TLS_CERT_FILENAME=fullchain.pem
TLS_KEY_FILENAME=privkey.pem
BACKEND_CORS_ORIGINS=["https://ecg.your-domain.com"]
```

When TLS is enabled:

- the deployment script automatically adds `docker-compose.prod.tls.yml`
- Docker publishes `443`, and Nginx listens on `443`
- requests on `80` redirect to HTTPS, except `/health`
- the backend receives `X-Forwarded-Proto=https`

If you prefer external TLS termination instead, leave `ENABLE_TLS=False` and put this stack behind your cloud load balancer or another reverse proxy.

## 13. Backups

Persistent data lives in:

- Docker volume: MySQL data
- [data/uploads](/Users/azure/ECG-Diagnosis-Suite/data/uploads)
- [data/reports](/Users/azure/ECG-Diagnosis-Suite/data/reports)
- [models/](/Users/azure/ECG-Diagnosis-Suite/models)

At minimum, back up:

- the MySQL volume
- the `models/` directory
- the `data/` directory
- `.env.production`

## 14. Security Notes

- Keep `.env.production` out of Git
- Use long random secrets and strong DB passwords
- Do not expose `3306` or `8000`
- Keep `BACKEND_API_DOCS_ENABLED=False` unless you explicitly need docs
- Restrict SSH access where possible
- Apply OS security updates regularly

## 15. Troubleshooting

If `reverse-proxy` is up but the page is blank:

- check frontend logs
- confirm `frontend` container is running
- confirm `docker compose ... ps` shows all services healthy

If API requests fail:

- check backend logs
- check `/health`
- verify model checkpoint path exists
- verify MySQL credentials in `.env.production`

If login or refresh fails in browser:

- confirm `APP_DOMAIN`, `BACKEND_CORS_ORIGINS`, and `BACKEND_ALLOWED_HOSTS` all match the real domain
- clear old browser cookies after changing domains

If deployment fails after `git pull`:

- rerun `bash deploy.sh`
- inspect `docker compose --env-file .env.production -f docker-compose.prod.yml logs -f`

## 16. Minimal Deployment Checklist

- server created
- `22` and `80` open
- domain pointed at the server
- repository cloned
- `.env.production` created and edited
- model checkpoint copied into `models/`
- `bash deploy.sh` completed successfully
- browser can open the site
- `/health` returns a valid response
