from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse, RedirectResponse

from app.services import uploads as uploads_service

# Local backend: signed links to private uploads (payment screenshots).
private_router = APIRouter(prefix="/api/v1/uploads/private", tags=["uploads"])

# S3 backend: public upload paths redirect to a presigned S3 URL.
public_s3_router = APIRouter(prefix="/uploads", tags=["uploads"])


@private_router.get("/{filename}")
def get_private_upload(filename: str, expires: int = Query(), signature: str = Query()):
    path = uploads_service.local_private_path(filename, expires, signature)
    if path is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Link is invalid or has expired")
    return FileResponse(path, headers={"Cache-Control": "private, max-age=300"})


@public_s3_router.get("/{filename}")
def get_public_upload(filename: str):
    return RedirectResponse(
        uploads_service.public_redirect_url(filename),
        status_code=status.HTTP_302_FOUND,
        headers={"Cache-Control": "public, max-age=600"},
    )
