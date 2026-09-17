import httpx
from fastapi import Request, Response
from fastapi.responses import JSONResponse

# from common.logging import request_id_var

_STRIP_HEADERS = {"host", "content-length", "x-user-id"}


async def forward_request(
    request: Request,
    base_url: str,
    path: str,
    extra_headers: dict[str, str] | None = None,
) -> Response:
    target_url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in _STRIP_HEADERS
    }
    if extra_headers:
        headers.update(extra_headers)

    body = await request.body()

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            upstream = await client.request(
                request.method,
                target_url,
                headers=headers,
                content=body,
            )
        except httpx.RequestError as exc:
            return JSONResponse(
                status_code=502,
                content={"detail": f"Upstream service unavailable: {exc}"},
            )

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers={
            key: value
            for key, value in upstream.headers.items()
            if key.lower() not in {"content-encoding", "transfer-encoding", "connection"}
        },
        media_type=upstream.headers.get("content-type"),
    )
