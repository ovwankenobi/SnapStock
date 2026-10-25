"""Image uploads, stored on local disk (development) or in S3 (production).

Two visibility levels:

- **Public** (product photos, payout QR codes): stored as `/uploads/<file>` and readable by
  anyone with the link. Locally that path is served straight from `UPLOAD_DIR`; with S3 the
  backend redirects it to a short-lived presigned URL, so the bucket itself stays private.
- **Private** (buyers' payment screenshots): the database holds a storage key
  (`private/<file>`), never a URL. Responses turn it into a short-lived signed URL with
  `private_url`, and only for the seller or buyer of that sale.
"""

import functools
import hashlib
import hmac
import time
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import settings

ALLOWED_PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp"}
PUBLIC_PATH_PREFIX = "/uploads/"
PRIVATE_KEY_PREFIX = "private/"
PRIVATE_LOCAL_ROUTE = "/api/v1/uploads/private/"
# Signed URLs expire on a fixed grid, so the same file keeps the same URL for a while
# and browsers can cache the image instead of re-downloading it on every refetch.
_URL_GRID_SECONDS = 300


class InvalidImageError(Exception):
    pass


def validate_image(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_PHOTO_TYPES:
        raise InvalidImageError("Photo must be a JPEG, PNG, or WebP image")
    if file.size is not None and file.size > settings.MAX_UPLOAD_BYTES:
        raise InvalidImageError(_too_large_message())


def save_image(file: UploadFile, prefix: str, private: bool = False) -> str:
    """Validate and store an uploaded image.

    Returns the public `/uploads/...` path, or for `private=True` the storage key to keep in
    the database and pass to `private_url` when returning it.
    """
    validate_image(file)
    data = file.file.read(settings.MAX_UPLOAD_BYTES + 1)
    if len(data) > settings.MAX_UPLOAD_BYTES:
        raise InvalidImageError(_too_large_message())

    extension = Path(file.filename or "").suffix.lower() or ".jpg"
    filename = f"{prefix}_{uuid.uuid4().hex}{extension}"

    if settings.STORAGE_BACKEND == "s3":
        key = f"{PRIVATE_KEY_PREFIX if private else 'public/'}{filename}"
        _s3().put_object(Bucket=settings.S3_BUCKET, Key=key, Body=data, ContentType=file.content_type)
    else:
        directory = Path(settings.PRIVATE_UPLOAD_DIR if private else settings.UPLOAD_DIR)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / filename).write_bytes(data)

    return f"{PRIVATE_KEY_PREFIX}{filename}" if private else f"{PUBLIC_PATH_PREFIX}{filename}"


def private_url(key: str | None) -> str | None:
    """A short-lived URL for a private upload. Only call this for a viewer allowed to see it."""
    if key is None:
        return None
    if not key.startswith(PRIVATE_KEY_PREFIX):
        # Proofs uploaded before private storage existed were saved as public paths.
        return key

    if settings.STORAGE_BACKEND == "s3":
        return _s3().generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET, "Key": key},
            ExpiresIn=settings.PRIVATE_URL_TTL_SECONDS,
        )

    filename = key.removeprefix(PRIVATE_KEY_PREFIX)
    expires = _grid_expiry()
    return f"{PRIVATE_LOCAL_ROUTE}{filename}?expires={expires}&signature={_sign(filename, expires)}"


def public_redirect_url(filename: str) -> str:
    """S3 only: a presigned URL for a public upload, which `/uploads/<file>` redirects to."""
    return _s3().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET, "Key": f"public/{filename}"},
        ExpiresIn=settings.PUBLIC_URL_TTL_SECONDS,
    )


def local_private_path(filename: str, expires: int, signature: str) -> Path | None:
    """Local backend: the file behind a signed private URL, or None if the link is invalid or expired."""
    if expires < time.time() or not hmac.compare_digest(signature, _sign(filename, expires)):
        return None
    directory = Path(settings.PRIVATE_UPLOAD_DIR).resolve()
    path = (directory / filename).resolve()
    if path.parent != directory or not path.is_file():
        return None
    return path


def _grid_expiry() -> int:
    now = int(time.time())
    return (now // _URL_GRID_SECONDS + 1) * _URL_GRID_SECONDS + settings.PRIVATE_URL_TTL_SECONDS


def _sign(filename: str, expires: int) -> str:
    message = f"{filename}:{expires}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()


def _too_large_message() -> str:
    return f"Photo must be {settings.MAX_UPLOAD_BYTES // (1024 * 1024)} MB or smaller"


@functools.cache
def _s3():
    import boto3
    from botocore.config import Config

    # Regional endpoint: presigned URLs on the global one can fail for buckets outside us-east-1.
    return boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        endpoint_url=f"https://s3.{settings.AWS_REGION}.amazonaws.com",
        config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
    )
