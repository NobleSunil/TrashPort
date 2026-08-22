# TrashPort Production Deployment Guide

## Architecture Overview
- **Application Server:** Gunicorn or Uvicorn with ASGI support.
- **Reverse Proxy:** Nginx with SSL termination via Let's Encrypt.
- **Database:** Managed PostgreSQL (Cloud SQL / AWS RDS).
- **Background Tasks:** Redis + Celery.
- **Static & Media:** WhiteNoise or Amazon S3 / Google Cloud Storage.

## Docker Deployment
```bash
docker compose -f docker-compose.production.yml up --build -d
```

## Environment Variables
Ensure all production keys in `.env` are populated (see `.env.example`).
