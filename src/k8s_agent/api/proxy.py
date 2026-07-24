import json

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import Response, StreamingResponse

from k8s_agent.api.agents import AgentChatRequest
from k8s_agent.core.config import settings
from k8s_agent.services.agents import build_agent_input
from k8s_agent.team import direct_agents, get_agent_profiles

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


def _operator_compatibility_plan(req: AgentChatRequest) -> str:
    goal = " ".join(req.message.split())
    evidence = [
        " ".join(item.split())[:280]
        for item in req.context
        if item.strip()
    ]
    evidence_lines = (
        "\n".join(
            f"- 证据 {index + 1}：{item}"
            for index, item in enumerate(evidence)
        )
        if evidence
        else "- 尚未提供共享证据，执行前需要先由侦察员确认目标资源现状。"
    )
    return (
        "> 当前远端后端尚未部署独立操作员接口。以下为安全兼容方案草案，"
        "不会执行任何集群命令。\n\n"
        f"## 变更目标\n{goal}\n\n"
        f"## 已有证据\n{evidence_lines}\n\n"
        "## 执行前检查\n"
        "1. 确认目标集群、命名空间、资源类型和资源名称。\n"
        "2. 保存当前配置、Pod 状态、事件及关键指标作为基线。\n"
        "3. 核对业务影响窗口、依赖关系和可用副本数量。\n\n"
        "## 建议步骤\n"
        "1. 先让侦察员补齐目标资源的只读证据。\n"
        "2. 根据证据生成最小变更内容，并进行 dry-run 或差异检查。\n"
        "3. 经人工确认后，再通过受控发布流程执行变更。\n"
        "4. 持续观察工作负载状态、事件、日志和服务指标。\n\n"
        "## 验证与回滚\n"
        "- 验证：资源就绪、错误率无上升、关键指标恢复且无新增 Warning 事件。\n"
        "- 回滚：恢复已保存配置或回退到上一稳定版本，并重新执行相同验证。"
    )


async def _relay_stream(upstream):
    if upstream.status_code >= 400:
        message = f"后端服务返回错误 ({upstream.status_code})"
        yield f"data: {json.dumps({'error': message}, ensure_ascii=False)}\n\n"
        return
    async for chunk in upstream.aiter_raw():
        yield chunk


def _stream_chat(
    request: Request,
    target: str,
    body: bytes,
    fallback_target: str | None = None,
    fallback_body: bytes | None = None,
    fallback_content: str | None = None,
) -> StreamingResponse:
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
                    if upstream.status_code != 404:
                        async for chunk in _relay_stream(upstream):
                            yield chunk
                        return
                    if fallback_content is not None:
                        payload = {"agent": "operator", "content": fallback_content}
                        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                        yield "data: [DONE]\n\n"
                        return
                    if not fallback_target:
                        async for chunk in _relay_stream(upstream):
                            yield chunk
                        return

                async with client.stream(
                    request.method,
                    fallback_target,
                    content=fallback_body,
                    headers={"accept": "text/event-stream", "content-type": "application/json"},
                ) as upstream:
                    async for chunk in _relay_stream(upstream):
                        yield chunk
        except httpx.RequestError as exc:
            message = f"无法连接后端服务：{exc}"
            yield f"data: {json.dumps({'error': message}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/backend/api/agents")
async def proxy_agent_profiles():
    return {"agents": get_agent_profiles()}


@router.post("/backend/api/agents/{agent_id}/chat")
async def proxy_agent_chat(agent_id: str, req: AgentChatRequest, request: Request):
    if agent_id not in direct_agents:
        return Response(
            content=json.dumps({"detail": "Agent 不存在"}, ensure_ascii=False),
            status_code=404,
            media_type="application/json",
        )

    direct_body = req.model_dump_json().encode()
    directed_input = build_agent_input(req.message, req.context)
    profile = next(item for item in get_agent_profiles() if item["id"] == agent_id)
    safety = f"只委派给 {profile['english_name']}，不要让其他成员参与。"
    fallback_message = (
        f"[专家定向模式]\n{safety}\n"
        f"请以 {profile['name']} 身份直接回答，不要输出协调过程。\n\n"
        f"{directed_input}"
    )
    fallback_body = json.dumps(
        {
            "message": fallback_message,
            "session_id": f"agent-{agent_id}-{req.session_id}",
        },
        ensure_ascii=False,
    ).encode()
    return _stream_chat(
        request,
        _target_url(f"api/agents/{agent_id}/chat"),
        direct_body,
        fallback_target=None if agent_id == "operator" else _target_url("api/chat"),
        fallback_body=None if agent_id == "operator" else fallback_body,
        fallback_content=(
            _operator_compatibility_plan(req)
            if agent_id == "operator"
            else None
        ),
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
