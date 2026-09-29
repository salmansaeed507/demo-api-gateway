import re
import uuid
from functools import lru_cache
from pathlib import PurePosixPath

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from fastapi import HTTPException, status

from .config import settings

_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


def s3_configured() -> bool:
    return bool(
        settings.aws_access_key_id
        and settings.aws_secret_access_key
        and settings.s3_bucket
    )


def require_s3_configured() -> None:
    if not s3_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="S3 is not configured",
        )


@lru_cache(maxsize=1)
def get_s3_client() -> BaseClient:
    kwargs: dict = {
        "service_name": "s3",
        "aws_access_key_id": settings.aws_access_key_id,
        "aws_secret_access_key": settings.aws_secret_access_key,
        "region_name": settings.aws_region,
        "config": Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    }
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
    return boto3.client(**kwargs)


def build_object_key(filename: str | None = None) -> str:
    prefix = settings.s3_key_prefix.strip().strip("/")
    unique = uuid.uuid4().hex
    if filename:
        safe = _SAFE_FILENAME.sub("_", PurePosixPath(filename).name).strip("._")
        name = f"{unique}_{safe}" if safe else unique
    else:
        name = unique
    return f"{prefix}/{name}" if prefix else name


def assert_key_allowed(key: str) -> None:
    cleaned = key.lstrip("/")
    if not cleaned or ".." in cleaned.split("/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid object key",
        )
    prefix = settings.s3_key_prefix.strip().strip("/")
    if prefix and not (cleaned == prefix or cleaned.startswith(f"{prefix}/")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Object key is outside the configured prefix",
        )


def presign_upload(key: str, content_type: str) -> str:
    return get_s3_client().generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": settings.s3_bucket,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=settings.s3_presign_expires_seconds,
    )


def presign_download(key: str) -> str:
    return get_s3_client().generate_presigned_url(
        ClientMethod="get_object",
        Params={
            "Bucket": settings.s3_bucket,
            "Key": key,
        },
        ExpiresIn=settings.s3_presign_expires_seconds,
    )


def public_object_url(key: str) -> str:
    """Stable path-style object URL (not signed). Needs public-read or a CDN in front."""
    base = (settings.s3_public_base_url or settings.s3_endpoint_url).rstrip("/")
    if base:
        return f"{base}/{settings.s3_bucket}/{key}"
    return (
        f"https://{settings.s3_bucket}.s3.{settings.aws_region}.amazonaws.com/{key}"
    )
