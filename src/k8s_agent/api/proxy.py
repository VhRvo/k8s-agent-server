import json

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import Response, StreamingResponse

from k8s_agent.core.config import settings

router = APIRouter()

_TIMEOUT = httpx.Timeout(connect=5.0, read=30.0, write=30.0, pool=5.0)
_STREAM_TIMEOUT = httpx.Timeout(connect=5.0, read=None, write=30.0, pool=5.0)


def _target_url(path: str) -> str:
    return f"{settings.upstream_api_base_url.rstrip('/')}/{path.lstrip('/')}"


def _request_headers(request: Request) -> dict[str, str]:
    headers = {"accept": request.headers.get("accept", "*/*")}
    if content_type := request.headers.get("content-type"):
        headers["content-type"] = content_type
    return headers


def _stream_chat(request: Request, target: str, body: bytes) -> StreamingResponse:
    async def event_stream():
        try:
            async with httpx.AsyncClient(timeout=_STREAM_TIMEOUT) as client:
                async with client.stream(
                    request.method,
                    target,
                    params=list(request.query_params.multi_items()),
                    content=body,
                    headers=_request_headers(request),
                ) as upstream:
                    if upstream.status_code >= 400:
                        message = f"后端服务返回错误 ({upstream.status_code})"
                        yield f"data: {json.dumps({'error': message}, ensure_ascii=False)}\n\n"
                        return
                    async for chunk in upstream.aiter_raw():
                        yield chunk
        except httpx.RequestError as exc:
            message = f"无法连接后端服务：{exc}"
            yield f"data: {json.dumps({'error': message}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.api_route("/backend/{path:path}", methods=["GET", "POST", "DELETE"])
async def proxy_backend(path: str, request: Request):
    target = _target_url(path)
    body = await request.body()
    if path == "api/chat" and request.method == "POST":
        return _stream_chat(request, target, body)

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            upstream = await client.request(
                request.method,
                target,
                params=list(request.query_params.multi_items()),
                content=body,
                headers=_request_headers(request),
            )
    except httpx.RequestError as exc:
        return Response(
            content=json.dumps(
                {"detail": f"无法连接后端服务：{exc}"},
                ensure_ascii=False,
            ),
            status_code=502,
            media_type="application/json",
        )

    response_headers = {}
    if content_type := upstream.headers.get("content-type"):
        response_headers["content-type"] = content_type
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
    )
