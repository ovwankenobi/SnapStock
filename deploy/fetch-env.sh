#!/bin/sh
# Writes .env.prod from the SSM parameters under /snapstock/prod/ (run on the EC2 instance,
# which reads them through its instance role). Parameter names become variable names, e.g.
# /snapstock/prod/DATABASE_URL -> DATABASE_URL=...
set -eu

PARAM_PATH="${PARAM_PATH:-/snapstock/prod/}"
REGION="${AWS_REGION:-ap-southeast-2}"
OUT="$(dirname "$0")/.env.prod"

umask 077
aws ssm get-parameters-by-path \
  --region "$REGION" \
  --path "$PARAM_PATH" \
  --with-decryption \
  --recursive \
  --query 'Parameters[].[Name,Value]' \
  --output text |
  while IFS="$(printf '\t')" read -r name value; do
    printf '%s=%s\n' "${name##*/}" "$value"
  done > "$OUT.tmp"

if [ ! -s "$OUT.tmp" ]; then
  rm -f "$OUT.tmp"
  echo "No parameters found under $PARAM_PATH" >&2
  exit 1
fi
mv "$OUT.tmp" "$OUT"
echo "Wrote $(wc -l < "$OUT") settings to $OUT"
