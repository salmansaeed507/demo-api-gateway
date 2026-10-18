import httpx
from fastapi import Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

# from common.logging import request_id_var

_STRIP_HEADERS = {"host", "content-length", "x-user-id"}
_STRIP_RESPONSE_HEADERS = {"content-encoding", "transfer-encoding", "connection"}
# Proxied streams (e.g. SSE) can outlive a short read timeout.
_PROXY_TIMEOUT = httpx.Timeout(connect=30.0, read=None, write=30.0, pool=30.0)


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

    client = httpx.AsyncClient(timeout=_PROXY_TIMEOUT)
    try:
        upstream = await client.send(
            client.build_request(
                request.method,
                target_url,
                headers=headers,
                content=body,
            ),
            stream=True,
        )
    except httpx.RequestError as exc:
        await client.aclose()
        return JSONResponse(
            status_code=502,
            content={"detail": f"Upstream service unavailable: {exc}"},
        )

    response_headers = {
        key: value
        for key, value in upstream.headers.items()
        if key.lower() not in _STRIP_RESPONSE_HEADERS
    }

    async def stream_body():
        try:
            async for chunk in upstream.aiter_bytes():
                yield chunk
        finally:
            await upstream.aclose()
            await client.aclose()

    return StreamingResponse(
        stream_body(),
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )
