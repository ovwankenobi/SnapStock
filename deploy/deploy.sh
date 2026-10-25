#!/usr/bin/env bash
# Phase 3 deploy (see deployment.md): builds the frontend locally, ships it with the backend source
# through the deploy bucket, then builds the backend image on the (arm64) instance and restarts the
# stack via SSM Run Command (no SSH). Building on the instance avoids slow arm64 emulation locally.
#
#   AWS_PROFILE=<profile> ./deploy/deploy.sh               # build and deploy a new release
#   AWS_PROFILE=<profile> TAG=<tag> ./deploy/deploy.sh     # roll back to an uploaded release
#
# Releases stay in the deploy bucket for 30 days (its lifecycle rule).
set -euo pipefail

export AWS_REGION="${AWS_REGION:-ap-southeast-2}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUCKET="$(aws s3api list-buckets --query "Buckets[?starts_with(Name, 'snapstock-deploy-')].Name | [0]" --output text)"
INSTANCE_ID="$(aws ec2 describe-instances \
  --filters Name=tag:Name,Values=snapstock-web Name=instance-state-name,Values=running \
  --query 'Reservations[0].Instances[0].InstanceId' --output text)"
[ "$BUCKET" != "None" ] && [ "$INSTANCE_ID" != "None" ] || { echo "Run deploy/infra.sh first" >&2; exit 1; }

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

if [ -z "${TAG:-}" ]; then
  TAG="$(date -u +%Y%m%d-%H%M%S)-$(cd "$ROOT" && git rev-parse --short HEAD)"

  echo "== Building frontend"
  # VITE_API_URL=/api/v1 comes from frontend/.env. Don't pass it inline: Git Bash rewrites
  # /api/v1 into a Windows path (C:/Program Files/Git/api/v1) on its way to node.
  (cd "$ROOT/frontend" && npm ci && npm run build)
  grep -q 'baseURL:`/api/v1`' "$ROOT"/frontend/dist/assets/*.js ||
    { echo "Frontend build does not use VITE_API_URL=/api/v1; aborting" >&2; exit 1; }

  echo "== Uploading release $TAG"
  mkdir -p "$WORK/bundle/backend"
  cp -r "$ROOT/frontend/dist" "$ROOT/deploy/Caddyfile" "$ROOT/deploy/docker-compose.prod.yml" \
    "$ROOT/deploy/fetch-env.sh" "$WORK/bundle/"
  # Never ship local secrets, virtualenvs or dev uploads.
  tar -cf - -C "$ROOT/backend" --exclude=.env --exclude='.venv*' --exclude=uploads \
    --exclude=uploads_private --exclude=__pycache__ --exclude=.pytest_cache --exclude='*.log' \
    --exclude=tests . | tar -xf - -C "$WORK/bundle/backend"
  tar -czf "$WORK/bundle.tar.gz" -C "$WORK/bundle" .
  aws s3 cp "$WORK/bundle.tar.gz" "s3://$BUCKET/releases/$TAG/bundle.tar.gz"
fi

echo "== Deploying $TAG to $INSTANCE_ID"
# dist/ is emptied in place rather than replaced: Caddy bind-mounts the directory, and a new
# directory would leave the running container serving the deleted one.
cat > "$WORK/commands.json" <<EOF
{"commands": [
  "set -eu",
  "cd /opt/snapstock",
  "export AWS_REGION=$AWS_REGION",
  "aws s3 cp s3://$BUCKET/releases/$TAG/bundle.tar.gz /tmp/bundle.tar.gz",
  "mkdir -p dist && find dist -mindepth 1 -delete && rm -rf backend",
  "tar -xzf /tmp/bundle.tar.gz -C /opt/snapstock",
  "rm -f /tmp/bundle.tar.gz",
  "docker build -q -t snapstock-backend:$TAG backend",
  "sh fetch-env.sh",
  "echo BACKEND_TAG=$TAG > .env",
  "docker compose -f docker-compose.prod.yml up -d --wait",
  "docker image prune -af --filter until=720h",
  "docker compose -f docker-compose.prod.yml ps"
]}
EOF
CMD_ID="$(aws ssm send-command --instance-ids "$INSTANCE_ID" --document-name AWS-RunShellScript \
  --comment "snapstock deploy $TAG" --timeout-seconds 900 \
  --parameters "file://$(cygpath -m "$WORK/commands.json" 2>/dev/null || echo "$WORK/commands.json")" --query Command.CommandId --output text)"
aws ssm wait command-executed --command-id "$CMD_ID" --instance-id "$INSTANCE_ID" || true
aws ssm get-command-invocation --command-id "$CMD_ID" --instance-id "$INSTANCE_ID" \
  --query '[Status,StandardOutputContent,StandardErrorContent]' --output text
STATUS="$(aws ssm get-command-invocation --command-id "$CMD_ID" --instance-id "$INSTANCE_ID" \
  --query Status --output text)"
[ "$STATUS" = "Success" ] || { echo "Deploy $TAG failed ($STATUS)" >&2; exit 1; }
echo "Deployed $TAG"
