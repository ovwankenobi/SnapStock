import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import settings

ALLOWED_PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp"}


class InvalidImageError(Exception):
    pass


def validate_image(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_PHOTO_TYPES:
        raise InvalidImageError("Photo must be a JPEG, PNG, or WebP image")


def save_image(file: UploadFile, prefix: str) -> str:
    """Validate and store an uploaded image, returning its public `/uploads/...` path."""
    validate_image(file)

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    extension = Path(file.filename or "").suffix.lower() or ".jpg"
    filename = f"{prefix}_{uuid.uuid4().hex}{extension}"
    destination = upload_dir / filename

    with destination.open("wb") as buffer:
        buffer.write(file.file.read())

    return f"/uploads/{filename}"
