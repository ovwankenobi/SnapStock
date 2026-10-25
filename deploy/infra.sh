#!/usr/bin/env bash
# Phase 1 infrastructure (see deployment.md): security groups, RDS PostgreSQL, S3 buckets,
# EC2 instance role, SSM parameters, EC2 instance with an Elastic IP.
# RDS backup retention is 1 day because the free account plan caps it; set DB_BACKUP_DAYS=7
# after upgrading the plan (and run `aws rds modify-db-instance --backup-retention-period 7`).
#
# Get-or-create for every resource, so it is safe to re-run. Run from any machine with the
# AWS CLI signed in to the SnapStock project:
#   AWS_PROFILE=<profile> ./deploy/infra.sh
# Prints the Elastic IP at the end; point snapstock.duckdns.org at it.
set -euo pipefail
export MSYS_NO_PATHCONV=1  # Git Bash: keep /snapstock/... parameter names intact

export AWS_REGION="${AWS_REGION:-ap-southeast-2}"
DOMAIN="${DOMAIN:-snapstock.duckdns.org}"
PARAM_PATH="/snapstock/prod"
DB_ID="snapstock-prod"
DB_NAME="pos_system"
DB_USER="snapstock"
ROLE="snapstock-ec2"
TAGS="Key=project,Value=snapstock"

log() { printf '\n== %s\n' "$*"; }
none() { [ -z "$1" ] || [ "$1" = "None" ]; }

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
VPC_ID="$(aws ec2 describe-vpcs --filters Name=is-default,Values=true --query 'Vpcs[0].VpcId' --output text)"
SUBNETS="$(aws ec2 describe-subnets --filters Name=vpc-id,Values="$VPC_ID" --query 'Subnets[].SubnetId' --output text)"
echo "Region $AWS_REGION, VPC $VPC_ID"

# --- Security groups ---------------------------------------------------------
sg_id() {
  aws ec2 describe-security-groups --filters Name=vpc-id,Values="$VPC_ID" Name=group-name,Values="$1" \
    --query 'SecurityGroups[0].GroupId' --output text
}
ensure_sg() {
  local id; id="$(sg_id "$1")"
  if none "$id"; then
    id="$(aws ec2 create-security-group --vpc-id "$VPC_ID" --group-name "$1" --description "$2" \
      --tag-specifications "ResourceType=security-group,Tags=[{$TAGS}]" --query GroupId --output text)"
  fi
  echo "$id"
}
allow() {  # ignore "already exists" so re-runs are clean
  aws ec2 authorize-security-group-ingress "$@" >/dev/null 2>&1 || true
}

log "Security groups"
WEB_SG="$(ensure_sg snapstock-web 'SnapStock web: HTTP/HTTPS from anywhere, no SSH (use SSM)')"
DB_SG="$(ensure_sg snapstock-db 'SnapStock RDS: Postgres from snapstock-web only')"
for port in 80 443; do
  allow --group-id "$WEB_SG" --ip-permissions \
    "IpProtocol=tcp,FromPort=$port,ToPort=$port,IpRanges=[{CidrIp=0.0.0.0/0}],Ipv6Ranges=[{CidrIpv6=::/0}]"
done
allow --group-id "$WEB_SG" --ip-permissions \
  "IpProtocol=udp,FromPort=443,ToPort=443,IpRanges=[{CidrIp=0.0.0.0/0}],Ipv6Ranges=[{CidrIpv6=::/0}]"
allow --group-id "$DB_SG" --ip-permissions \
  "IpProtocol=tcp,FromPort=5432,ToPort=5432,UserIdGroupPairs=[{GroupId=$WEB_SG}]"
echo "web $WEB_SG, db $DB_SG"

# --- S3 buckets --------------------------------------------------------------
find_bucket() {
  aws s3api list-buckets --query "Buckets[?starts_with(Name, '$1')].Name | [0]" --output text
}
ensure_bucket() {  # $1 = name prefix; private, encrypted, tagged
  local name; name="$(find_bucket "$1")"
  if none "$name"; then
    name="$1$(openssl rand -hex 4)"
    aws s3api create-bucket --bucket "$name" \
      --create-bucket-configuration LocationConstraint="$AWS_REGION" >/dev/null
  fi
  aws s3api put-public-access-block --bucket "$name" --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
  aws s3api put-bucket-encryption --bucket "$name" --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
  aws s3api put-bucket-tagging --bucket "$name" --tagging "TagSet=[{$TAGS}]"
  echo "$name"
}

log "S3 buckets"
UPLOADS_BUCKET="$(ensure_bucket snapstock-uploads-)"
aws s3api put-bucket-versioning --bucket "$UPLOADS_BUCKET" --versioning-configuration Status=Enabled
# Old versions are only for recovering from mistakes; don't keep them forever.
aws s3api put-bucket-lifecycle-configuration --bucket "$UPLOADS_BUCKET" --lifecycle-configuration \
  '{"Rules":[{"ID":"expire-old-versions","Status":"Enabled","Filter":{},"NoncurrentVersionExpiration":{"NoncurrentDays":30}}]}'
# Build artifacts (frontend dist, backend image) on their way to the instance.
DEPLOY_BUCKET="$(ensure_bucket snapstock-deploy-)"
aws s3api put-bucket-lifecycle-configuration --bucket "$DEPLOY_BUCKET" --lifecycle-configuration \
  '{"Rules":[{"ID":"expire-artifacts","Status":"Enabled","Filter":{},"Expiration":{"Days":30}}]}'
echo "uploads $UPLOADS_BUCKET, deploy $DEPLOY_BUCKET"

# --- RDS PostgreSQL ----------------------------------------------------------
log "RDS PostgreSQL ($DB_ID)"
if ! aws rds describe-db-subnet-groups --db-subnet-group-name snapstock-db >/dev/null 2>&1; then
  # shellcheck disable=SC2086
  aws rds create-db-subnet-group --db-subnet-group-name snapstock-db \
    --db-subnet-group-description "SnapStock RDS" --subnet-ids $SUBNETS --tags "$TAGS" >/dev/null
fi
DB_PASSWORD=""
if ! aws rds describe-db-instances --db-instance-identifier "$DB_ID" >/dev/null 2>&1; then
  DB_PASSWORD="$(openssl rand -hex 24)"
  aws rds create-db-instance --db-instance-identifier "$DB_ID" \
    --engine postgres --engine-version 16.15 --db-instance-class db.t4g.micro \
    --storage-type gp3 --allocated-storage 20 --storage-encrypted \
    --db-name "$DB_NAME" --master-username "$DB_USER" --master-user-password "$DB_PASSWORD" \
    --db-subnet-group-name snapstock-db --vpc-security-group-ids "$DB_SG" --no-publicly-accessible \
    --backup-retention-period "${DB_BACKUP_DAYS:-1}" --deletion-protection --copy-tags-to-snapshot \
    --auto-minor-version-upgrade --tags "$TAGS" >/dev/null
  echo "Creating; this takes ~10 minutes"
fi

# --- IAM role for the instance -----------------------------------------------
log "IAM role $ROLE"
if ! aws iam get-role --role-name "$ROLE" >/dev/null 2>&1; then
  aws iam create-role --role-name "$ROLE" --tags "$TAGS" --assume-role-policy-document \
    '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}' >/dev/null
fi
aws iam attach-role-policy --role-name "$ROLE" \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
aws iam put-role-policy --role-name "$ROLE" --policy-name snapstock-app --policy-document "$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
     "Resource": "arn:aws:s3:::$UPLOADS_BUCKET/*"},
    {"Effect": "Allow", "Action": "s3:GetObject", "Resource": "arn:aws:s3:::$DEPLOY_BUCKET/*"},
    {"Effect": "Allow", "Action": ["ssm:GetParametersByPath", "ssm:GetParameters", "ssm:GetParameter"],
     "Resource": ["arn:aws:ssm:$AWS_REGION:$ACCOUNT_ID:parameter$PARAM_PATH",
                  "arn:aws:ssm:$AWS_REGION:$ACCOUNT_ID:parameter$PARAM_PATH/*"]}
  ]
}
EOF
)"
if ! aws iam get-instance-profile --instance-profile-name "$ROLE" >/dev/null 2>&1; then
  aws iam create-instance-profile --instance-profile-name "$ROLE" --tags "$TAGS" >/dev/null
  aws iam add-role-to-instance-profile --instance-profile-name "$ROLE" --role-name "$ROLE"
  sleep 15  # new instance profiles take a moment before EC2 accepts them
fi

# --- SSM parameters ----------------------------------------------------------
log "SSM parameters under $PARAM_PATH"
put_param() {  # $1 name, $2 value, $3 type; never overwrites an existing value
  if ! aws ssm get-parameter --name "$PARAM_PATH/$1" >/dev/null 2>&1; then
    aws ssm put-parameter --name "$PARAM_PATH/$1" --value "$2" --type "$3" --tags "$TAGS" >/dev/null
    echo "set $1"
  fi
}
put_param SECRET_KEY "$(openssl rand -hex 48)" SecureString
put_param CORS_ORIGINS "[\"https://$DOMAIN\"]" String
put_param STORAGE_BACKEND s3 String
put_param S3_BUCKET "$UPLOADS_BUCKET" String
put_param AWS_REGION "$AWS_REGION" String

# --- EC2 instance + Elastic IP -----------------------------------------------
log "EC2 instance"
INSTANCE_ID="$(aws ec2 describe-instances \
  --filters Name=tag:Name,Values=snapstock-web Name=instance-state-name,Values=pending,running,stopping,stopped \
  --query 'Reservations[0].Instances[0].InstanceId' --output text)"
if none "$INSTANCE_ID"; then
  AMI="$(aws ssm get-parameter --name /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64 \
    --query Parameter.Value --output text)"
  USER_DATA="$(cat <<'EOF'
#!/bin/bash
set -eux
dnf install -y docker
systemctl enable --now docker
mkdir -p /usr/local/lib/docker/cli-plugins
curl -fsSL -o /usr/local/lib/docker/cli-plugins/docker-compose \
  https://github.com/docker/compose/releases/latest/download/docker-compose-linux-aarch64
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
mkdir -p /opt/snapstock
EOF
)"
  INSTANCE_ID="$(aws ec2 run-instances --image-id "$AMI" --instance-type t4g.small \
    --subnet-id "$(echo "$SUBNETS" | awk '{print $1}')" --security-group-ids "$WEB_SG" \
    --iam-instance-profile Name="$ROLE" \
    --metadata-options HttpTokens=required,HttpPutResponseHopLimit=2,HttpEndpoint=enabled \
    --block-device-mappings 'DeviceName=/dev/xvda,Ebs={VolumeSize=20,VolumeType=gp3,Encrypted=true}' \
    --user-data "$USER_DATA" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=snapstock-web},{$TAGS}]" \
      "ResourceType=volume,Tags=[{Key=Name,Value=snapstock-web},{$TAGS}]" \
    --query 'Instances[0].InstanceId' --output text)"
  echo "Launched $INSTANCE_ID"
fi
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID"

EIP_ALLOC="$(aws ec2 describe-addresses --filters Name=tag:Name,Values=snapstock-web \
  --query 'Addresses[0].AllocationId' --output text)"
if none "$EIP_ALLOC"; then
  EIP_ALLOC="$(aws ec2 allocate-address --domain vpc \
    --tag-specifications "ResourceType=elastic-ip,Tags=[{Key=Name,Value=snapstock-web},{$TAGS}]" \
    --query AllocationId --output text)"
fi
aws ec2 associate-address --allocation-id "$EIP_ALLOC" --instance-id "$INSTANCE_ID" >/dev/null
EIP="$(aws ec2 describe-addresses --allocation-ids "$EIP_ALLOC" --query 'Addresses[0].PublicIp' --output text)"

# --- DATABASE_URL (needs the RDS endpoint) -----------------------------------
log "Waiting for RDS"
aws rds wait db-instance-available --db-instance-identifier "$DB_ID"
DB_HOST="$(aws rds describe-db-instances --db-instance-identifier "$DB_ID" \
  --query 'DBInstances[0].Endpoint.Address' --output text)"
if [ -n "$DB_PASSWORD" ]; then
  put_param DATABASE_URL \
    "postgresql+psycopg2://$DB_USER:$DB_PASSWORD@$DB_HOST:5432/$DB_NAME?sslmode=require" SecureString
elif ! aws ssm get-parameter --name "$PARAM_PATH/DATABASE_URL" >/dev/null 2>&1; then
  echo "RDS exists but $PARAM_PATH/DATABASE_URL is missing; reset the master password and set it." >&2
  exit 1
fi

log "Done"
echo "Instance      $INSTANCE_ID"
echo "Elastic IP    $EIP   -> set $DOMAIN to this in DuckDNS"
echo "RDS endpoint  $DB_HOST"
echo "Uploads       $UPLOADS_BUCKET"
echo "Deploy bucket $DEPLOY_BUCKET"
