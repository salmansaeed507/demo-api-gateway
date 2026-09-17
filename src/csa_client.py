import httpx

from .config import settings


def _csa_url(path: str) -> str:
    return f"{settings.customer_support_url.rstrip('/')}/{path.lstrip('/')}"


def seed_csa_user(user_id: int) -> None:
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            _csa_url("/internal/seed"),
            headers={"X-User-Id": str(user_id)},
        )
        response.raise_for_status()


def purge_csa_user(user_id: int) -> None:
    with httpx.Client(timeout=30.0) as client:
        response = client.delete(
            _csa_url("/internal/data"),
            headers={"X-User-Id": str(user_id)},
        )
        response.raise_for_status()
