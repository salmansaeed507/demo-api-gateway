import re
import uuid
from functools import lru_cache
from pathlib import PurePosixPath

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from fastapi import HTTPException, status

from common.config import BaseAppSettings

_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")
_TMP_SEGMENT = "tmp"


def s3_configured(settings: BaseAppSettings) -> bool:
    return bool(
        settings.aws_access_key_id
        and settings.aws_secret_access_key
        and settings.s3_bucket
    )


def require_s3_configured(settings: BaseAppSettings) -> None:
    if not s3_configured(settings):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="S3 is not configured",
        )


@lru_cache(maxsize=4)
def _cached_client(
    access_key: str,
    secret_key: str,
    region: str,
    endpoint_url: str,
) -> BaseClient:
    kwargs: dict = {
        "service_name": "s3",
        "aws_access_key_id": access_key,
        "aws_secret_access_key": secret_key,
        "region_name": region,
        "config": Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    }
    if endpoint_url:
        kwargs["endpoint_url"] = endpoint_url
    return boto3.client(**kwargs)


def get_s3_client(settings: BaseAppSettings) -> BaseClient:
    return _cached_client(
        settings.aws_access_key_id,
        settings.aws_secret_access_key,
        settings.aws_region,
        settings.s3_endpoint_url or "",
    )


def _configured_prefix(settings: BaseAppSettings) -> str:
    return settings.s3_key_prefix.strip().strip("/")


def _join_key(*parts: str) -> str:
    return "/".join(p.strip("/") for p in parts if p and p.strip("/"))


def _unique_object_name(filename: str | None = None) -> str:
    unique = uuid.uuid4().hex
    if not filename:
        return unique
    safe = _SAFE_FILENAME.sub("_", PurePosixPath(filename).name).strip("._")
    return f"{unique}_{safe}" if safe else unique


def staging_prefix(settings: BaseAppSettings) -> str:
    return _join_key(_configured_prefix(settings), _TMP_SEGMENT)


def is_staging_key(settings: BaseAppSettings, key: str) -> bool:
    cleaned = key.lstrip("/")
    prefix = staging_prefix(settings)
    return cleaned == prefix or cleaned.startswith(f"{prefix}/")


def build_object_key(settings: BaseAppSettings, filename: str | None = None) -> str:
    """Build a staging (tmp) object key for new uploads."""
    return _join_key(staging_prefix(settings), _unique_object_name(filename))


def staging_to_final_key(settings: BaseAppSettings, staging_key: str) -> str:
    cleaned = staging_key.lstrip("/")
    prefix = staging_prefix(settings)
    if cleaned == prefix or not cleaned.startswith(f"{prefix}/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Object key is not in the staging prefix",
        )
    name = cleaned[len(prefix) + 1 :]
    if not name or ".." in name.split("/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid staging object key",
        )
    return _join_key(_configured_prefix(settings), name)


def assert_key_allowed(settings: BaseAppSettings, key: str) -> None:
    cleaned = key.lstrip("/")
    if not cleaned or ".." in cleaned.split("/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid object key",
        )
    prefix = _configured_prefix(settings)
    if prefix and not (cleaned == prefix or cleaned.startswith(f"{prefix}/")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Object key is outside the configured prefix",
        )


def assert_staging_key(settings: BaseAppSettings, key: str) -> None:
    assert_key_allowed(settings, key)
    if not is_staging_key(settings, key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Object key is not a staging key",
        )


def presign_upload(settings: BaseAppSettings, key: str, content_type: str) -> str:
    return get_s3_client(settings).generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": settings.s3_bucket,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=settings.s3_presign_expires_seconds,
    )


def presign_download(settings: BaseAppSettings, key: str) -> str:
    return get_s3_client(settings).generate_presigned_url(
        ClientMethod="get_object",
        Params={
            "Bucket": settings.s3_bucket,
            "Key": key,
        },
        ExpiresIn=settings.s3_presign_expires_seconds,
    )


def promote_object(settings: BaseAppSettings, staging_key: str) -> str:
    """Copy a staging object to its final key and delete the staging object."""
    assert_staging_key(settings, staging_key)
    final_key = staging_to_final_key(settings, staging_key)
    client = get_s3_client(settings)
    client.copy_object(
        Bucket=settings.s3_bucket,
        CopySource={"Bucket": settings.s3_bucket, "Key": staging_key.lstrip("/")},
        Key=final_key,
    )
    client.delete_object(
        Bucket=settings.s3_bucket,
        Key=staging_key.lstrip("/"),
    )
    return final_key


def public_object_url(settings: BaseAppSettings, key: str) -> str:
    """Stable path-style object URL (not signed). Needs public-read or a CDN in front."""
    base = (settings.s3_public_base_url or settings.s3_endpoint_url).rstrip("/")
    if base:
        return f"{base}/{settings.s3_bucket}/{key}"
    return (
        f"https://{settings.s3_bucket}.s3.{settings.aws_region}.amazonaws.com/{key}"
    )


def is_http_url(value: str) -> bool:
    return value.lower().startswith(("http://", "https://"))


def is_managed_object_key(settings: BaseAppSettings, key: str) -> bool:
    """True for non-URL keys inside the configured S3 prefix (or any key if prefix empty)."""
    cleaned = key.strip().lstrip("/")
    if not cleaned or is_http_url(cleaned):
        return False
    try:
        assert_key_allowed(settings, cleaned)
    except HTTPException:
        return False
    return True


def delete_object(settings: BaseAppSettings, key: str) -> None:
    """Delete an object key from the configured bucket."""
    assert_key_allowed(settings, key)
    require_s3_configured(settings)
    get_s3_client(settings).delete_object(
        Bucket=settings.s3_bucket,
        Key=key.lstrip("/"),
    )
