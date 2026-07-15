import logging
from datetime import datetime
from typing import Any, Optional

from agno.db import SessionType
from agno.session.agent import AgentSession

from k8s_agent.agent import agent
from k8s_agent.core.config import settings

logger = logging.getLogger(__name__)

TITLE_MAX = 30


def derive_title(text: str) -> str:
    cleaned = (text or "").strip().replace("\n", " ")
    if not cleaned:
        return "新对话"
    return cleaned[:TITLE_MAX]


def _session_title(session: AgentSession) -> str:
    data = getattr(session, "session_data", None) or {}
    name = data.get("session_name") if isinstance(data, dict) else None
    return name or "新对话"


def _format_ts(ts: Optional[int]) -> str:
    if not ts:
        return ""
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def serialize_session_summary(session: AgentSession) -> dict:
    return {
        "id": session.session_id,
        "title": _session_title(session),
        "created_at": _format_ts(getattr(session, "created_at", None)),
        "updated_at": _format_ts(getattr(session, "updated_at", None)),
    }


def _coerce_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(str(p) for p in content)
    return str(content)


def serialize_session_messages(session: AgentSession) -> dict:
    messages = []
    try:
        history = session.get_chat_history()
    except Exception:
        history = []
    for m in history or []:
        messages.append({"role": m.role, "content": _coerce_content(getattr(m, "content", None))})
    return {
        "id": session.session_id,
        "title": _session_title(session),
        "messages": messages,
    }


def list_conversations() -> list[dict]:
    try:
        sessions = agent.db.get_sessions(
            user_id=settings.agent_user_id,
            sort_by="created_at",
            sort_order="desc",
        )
    except Exception:
        logger.exception("列出会话失败")
        sessions = []
    if isinstance(sessions, tuple):
        sessions = sessions[0]
    items = [serialize_session_summary(s) for s in (sessions or [])]
    items.sort(key=lambda x: x["updated_at"] or x["created_at"], reverse=True)
    return items


def get_conversation(session_id: str) -> Optional[dict]:
    try:
        session = agent.get_session(session_id=session_id, user_id=settings.agent_user_id)
    except Exception:
        logger.exception("获取会话失败 session_id=%s", session_id)
        return None
    if session is None:
        return None
    return serialize_session_messages(session)


def delete_conversation(session_id: str) -> bool:
    try:
        agent.db.delete_session(session_id, user_id=settings.agent_user_id)
        return True
    except Exception:
        logger.exception("删除会话失败 session_id=%s", session_id)
        return False


def set_title_if_new(session_id: str, user_message: str) -> None:
    try:
        session = agent.get_session(session_id=session_id, user_id=settings.agent_user_id)
        if session is None:
            return
        title = _session_title(session)
        if title and title != "新对话":
            return
        agent.db.rename_session(
            session_id=session_id,
            session_type=SessionType.AGENT,
            session_name=derive_title(user_message),
            user_id=settings.agent_user_id,
        )
    except Exception:
        logger.exception("设置会话标题失败 session_id=%s", session_id)
