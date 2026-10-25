#!/bin/sh
set -e

alembic upgrade head

# --proxy-headers: take the client IP and scheme from Caddy's X-Forwarded-* headers so rate
# limits apply per visitor. Trusting every forwarder is safe only because the backend port is
# never published; Caddy is the one thing that can reach it.
exec uvicorn app.main:app --host 0.0.0.0 --port 6767 --proxy-headers --forwarded-allow-ips='*'
