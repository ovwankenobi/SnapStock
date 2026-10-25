# Deployment (AWS)

Plan and runbook for taking SnapStock from local development to production on AWS. Status checkboxes track progress; update them as steps land.

## Target architecture

```
https://<domain> ──► EC2 (t4g.small, Docker Compose, Elastic IP)
                      ├─ Caddy   — HTTPS via Let's Encrypt, serves frontend/dist,
                      │            reverse-proxies /api/* to the backend container
                      └─ backend — FastAPI + uvicorn, runs `alembic upgrade head` on start
                            ├──► RDS PostgreSQL 16 (db.t4g.micro, private subnet)
                            └──► S3 bucket (private) for uploaded images
```

Why this shape:

- **Same origin for frontend and API.** Caddy plays the role the Vite dev proxy plays locally (`/api` → backend), so `VITE_API_URL=/api/v1` and relative upload URLs keep working unchanged and CORS is not needed.
- **One instance is enough for now.** `slowapi` keeps rate-limit counters in memory, which is only correct with a single backend process host. Moving to multiple instances requires a shared store (Redis) first.
- **HTTPS is mandatory**, not optional: phone cameras (`getUserMedia`, image search) and service features only work on secure origins.
- **RDS instead of Postgres on the instance** for automated backups, point-in-time restore and minor-version patching.

Region: `ap-southeast-2` (Sydney). The AWS project can only create resources in its own region, so Singapore (`ap-southeast-1`, lower latency to the Philippines) is not available.

## Domain

Chosen domain: **`snapstock.duckdns.org`** (free)

[DuckDNS](https://www.duckdns.org) gives free subdomains of `duckdns.org`: sign in with GitHub/Google, claim `snapstock`, and point it at the EC2 Elastic IP. Let's Encrypt issues certificates for it, so Caddy's automatic HTTPS works unchanged. No Route 53 hosted zone is needed.

- Claimed on 2026-10-18.
- Why not the free AWS hostname: Let's Encrypt will not issue certificates for `*.amazonaws.com` EC2 hostnames, and phones need HTTPS for the camera.
- Trade-offs: looks less professional than an owned domain, and the app depends on DuckDNS staying up. The DuckDNS account token can repoint the name, so keep it private.
- Upgrading later: buy a domain (e.g. `snapstock.ph` / `snapstock.com.ph` at dot.ph, or `snapstock.shop` / `snapstockpos.com` in Route 53; `snapstock.app`, `snapstock.io` and `getsnapstock.com` are taken), point it at the same Elastic IP, add it to the Caddyfile and `CORS_ORIGINS`, and have Caddy redirect the DuckDNS name to it. Printed receipt QR codes encode the domain, so switch before printing many receipts.

## Prerequisites (owner only)

- [ ] AWS account with a payment method
- [ ] AWS Budgets alert (e.g. $40/month)
- [ ] AWS CLI v2 installed and `aws configure` done with an IAM admin user (region `ap-southeast-1`); `aws sts get-caller-identity` succeeds
- [x] DuckDNS account created and `snapstock` subdomain claimed (2026-10-18; currently points at the owner's home IP until the Elastic IP exists)
- [ ] Never commit or paste access keys anywhere; they live only in `~/.aws/credentials`

## Phase 0 — Code changes (local, no AWS needed)

- [x] **Uploads to S3.** *(done: `services/uploads.py` — public files keep `/uploads/<file>` paths, which the backend 302-redirects to a presigned S3 URL; payment proofs are stored as `private/<file>` keys and returned as 15-minute signed URLs; 5 MB limit)* `app/services/uploads.py` writes to local disk and `app/main.py` mounts `UPLOAD_DIR` at `/uploads` with no auth, so every file — including buyers' payment screenshots — is public to anyone with the URL. Change to:
  - a storage backend switch (`STORAGE_BACKEND=local|s3`) so local dev keeps using disk;
  - product photos and payout QR codes: readable by URL (public-read prefix or served via backend);
  - payment proofs (`payment_proof_url`): private prefix, returned only to the seller/buyer of that sale as short-lived presigned URLs (or streamed through an authenticated endpoint). They must never appear on the public receipt.
  - keep the existing `validate_image` checks; add a max file size.
- [x] **Backend `Dockerfile`** (Python 3.12 slim, non-root user), entrypoint runs `alembic upgrade head` then `uvicorn app.main:app --host 0.0.0.0 --port 6767 --proxy-headers`. Remove `pytest`/`httpx` from the runtime image (split into `requirements-dev.txt`).
- [x] **Production settings via environment**, not a committed `.env`:
  - `DATABASE_URL` — RDS endpoint, `sslmode=require`
  - `SECRET_KEY` — long random value (`python -c "import secrets; print(secrets.token_urlsafe(64))"`)
  - `CORS_ORIGINS` — `["https://<domain>"]`
  - `S3_BUCKET`, `AWS_REGION`, `STORAGE_BACKEND=s3`
  - Stored in SSM Parameter Store (SecureString) and loaded into the container env at deploy time by `deploy/fetch-env.sh` (writes `deploy/.env.prod`; see `deploy/.env.prod.example`).
- [x] **Rate limiting behind a proxy:** uvicorn runs with `--proxy-headers --forwarded-allow-ips='*'`, so `request.client` (and `slowapi`'s `get_remote_address`) is the real client IP from the `X-Forwarded-For` header Caddy overwrites. Safe only because the backend port is never published — Caddy is the only thing that can reach it.
- [x] **`deploy/docker-compose.prod.yml`** with `caddy` and `backend` services (no `db` — RDS replaces it).
- [x] **`deploy/Caddyfile`**: serve `frontend/dist` with SPA fallback to `index.html` (so `/r/:receiptCode` deep links work), proxy `/api/*`, gzip/zstd, long cache headers for hashed `assets/`, no-cache for `index.html`.
- [ ] Verify locally: `docker compose -f deploy/docker-compose.prod.yml up` against the local Postgres, full sale + buyer order + payment proof flow on a phone. *(2026-10-19: verified over HTTP on the PC with `SITE_ADDRESS=:80` — health, SPA deep links, cache headers, signed proof links, 5 MB/10 MB limits, spoofed `X-Forwarded-For` ignored. Phone test still to do.)*
- [ ] Health check already exists: `GET /api/v1/health`.

## Phase 1 — AWS infrastructure

Scripted in `deploy/infra.sh` (AWS CLI, get-or-create, safe to re-run). Created 2026-10-19.

- [x] Default VPC; RDS subnet group `snapstock-db` over its subnets (they are public subnets, but the instance has no public IP and its security group only admits `snapstock-web`)
- [x] Security groups
  - `snapstock-web`: inbound 80/443 from anywhere; no SSH — shell access is SSM Session Manager
  - `snapstock-db`: inbound 5432 only from `snapstock-web`
- [x] RDS PostgreSQL 16 (`snapstock-prod`, 16.15), `db.t4g.micro`, 20 GB gp3, not publicly accessible, automated backups 1 day (the free account plan's cap; raise to 7 after upgrading the plan — take a manual snapshot before each deploy meanwhile), deletion protection on
- [x] S3 bucket `snapstock-uploads-<suffix>`: Block Public Access on (files are served via presigned URLs), default encryption, versioning on (old versions expire after 30 days); plus `snapstock-deploy-<suffix>` for release bundles (expire after 30 days)
- [x] IAM role + instance profile (`snapstock-ec2`) for EC2: `s3:GetObject/PutObject/DeleteObject` on the bucket, `ssm:GetParameters*` on `/snapstock/*`, SSM managed instance core
- [x] SSM parameters under `/snapstock/prod/*`
- [x] EC2 `t4g.small` (Amazon Linux 2023, ARM), 20 GB gp3, Docker + Compose plugin, Elastic IP

## Phase 2 — Domain and HTTPS

- [x] In the DuckDNS dashboard, set `snapstock` → the Elastic IP (it's static, so no dynamic-update cron is needed)
- [x] `nslookup snapstock.duckdns.org` returns the Elastic IP
- [x] Caddy obtains and renews Let's Encrypt certificates automatically once DNS resolves (HTTP-01 challenge on port 80)

## Phase 3 — Deploy and go live

Deploy procedure (until CI exists): `AWS_PROFILE=<profile> ./deploy/deploy.sh`. It:

1. runs `npm ci && npm run build` in `frontend/` (with `VITE_API_URL=/api/v1`)
2. uploads `dist/`, `deploy/` files and the backend source (no `.env`, venvs or uploads) to the deploy bucket
3. via SSM Run Command on the instance: builds the backend image natively (arm64 — emulated builds on an x86 PC take 15+ minutes), runs `fetch-env.sh`, `docker compose up -d --wait` — migrations run on backend start
4. Rollback: `TAG=<previous release> ./deploy/deploy.sh` redeploys an uploaded release (kept 30 days)

First deploy: 2026-10-19 (`20261019-074439-83587fb`) — health, SPA deep links, HTTP→HTTPS redirect and the Let's Encrypt certificate verified.

5. Smoke test: `curl https://<domain>/api/v1/health`, log in, ring up a walk-in sale, place and approve a buyer order, open a public receipt QR

Go-live checklist:

- [ ] Do **not** run `scripts/seed.py` in production unless demo data is wanted
- [ ] Test on a real phone over mobile data, including going offline mid-session
- [ ] CloudWatch alarms: EC2 CPU and status check, RDS CPU / free storage / connections
- [ ] Confirm an RDS snapshot restores into a fresh instance (backups are only real once restored)

## Rollback

- App: redeploy the previous image tag / `dist` build.
- Schema: migrations run forward on deploy; take a manual RDS snapshot before any deploy that includes a migration, and restore from it rather than relying on `alembic downgrade` against live data.

## Estimated monthly cost (ap-southeast-1, on-demand)

| Item | ≈ USD / month |
|---|---|
| EC2 t4g.small + 20 GB gp3 | 14 |
| RDS db.t4g.micro + 20 GB gp3 | 16 |
| Public IPv4 (Elastic IP) | 3.60 |
| Domain (DuckDNS) | 0 |
| S3 + data transfer (low traffic) | < 2 |
| **Total** | **~ 35** |

New-account free-tier credits can offset much of the first months.

## Later, when usage grows

- Frontend on S3 + CloudFront; API behind an ALB on ECS Fargate (multiple tasks) — requires Redis-backed rate limiting first
- GitHub Actions: lint + tests on PR, build and deploy on merge to `main`
- RDS Multi-AZ, and a staging environment mirroring production
