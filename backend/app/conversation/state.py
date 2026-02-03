# state.py - v1.0
# In-memory session store for conversation (session_id -> messages, mode). Redis in Phase 2.
# Deps: none. Port: N/A.

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Literal

ConversationMode = Literal["expert", "balanced", "guided"]


@dataclass
class Message:
    role: Literal["user", "assistant"]
    content: str


@dataclass
class Session:
    session_id: str
    mode: ConversationMode
    messages: list[Message] = field(default_factory=list)

    def append(self, role: Literal["user", "assistant"], content: str) -> None:
        self.messages.append(Message(role=role, content=content))


_sessions: dict[str, Session] = {}


def create_or_update_session(
    session_id: str | None = None,
    mode: ConversationMode = "balanced",
) -> Session:
    """Create a new session or return existing. If session_id given and exists, update mode if needed."""
    if session_id and session_id in _sessions:
        s = _sessions[session_id]
        s.mode = mode
        return s
    sid = session_id or str(uuid.uuid4())
    s = Session(session_id=sid, mode=mode)
    _sessions[sid] = s
    return s


def get_session(session_id: str) -> Session | None:
    return _sessions.get(session_id)
