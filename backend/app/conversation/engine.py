# engine.py - v1.0
# Conversation turn via Anthropic Claude; supports optional image (vision) for architecture drawings.
# Deps: anthropic, state, prompts. Port: N/A.

from __future__ import annotations

import os
from typing import Any

from .prompts import get_system_prompt
from .state import ConversationMode, Session

def chat_turn(
    session: Session,
    user_message: str,
    image_base64: str | None = None,
    image_media_type: str | None = None,
) -> dict[str, Any]:
    """
    Call Claude with session history + current user message (and optional image). Append user + assistant to session.
    Returns { "reply": str, "session_id": str, "recommendation": None }.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        session.append("user", user_message)
        session.append(
            "assistant",
            "Conversation is not configured: ANTHROPIC_API_KEY is missing. Set it in .env to use the AI assistant.",
        )
        return {
            "reply": session.messages[-1].content,
            "session_id": session.session_id,
            "recommendation": None,
        }

    try:
        import anthropic
    except ImportError:
        session.append("user", user_message)
        session.append(
            "assistant",
            "Server error: anthropic package not installed. Add 'anthropic' to requirements.txt and reinstall.",
        )
        return {
            "reply": session.messages[-1].content,
            "session_id": session.session_id,
            "recommendation": None,
        }

    client = anthropic.Anthropic(api_key=api_key)
    system = get_system_prompt(session.mode)

    # Build messages: previous turns (text only) + current user turn (text + optional image)
    messages: list[dict[str, Any]] = [
        {"role": "user" if m.role == "user" else "assistant", "content": m.content}
        for m in session.messages
    ]
    if image_base64 and image_media_type:
        current_content: list[dict[str, Any]] = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": image_media_type,
                    "data": image_base64,
                },
            },
            {"type": "text", "text": user_message or "What do you see in this architecture drawing? Suggest a solution based on it."},
        ]
        messages.append({"role": "user", "content": current_content})
    else:
        messages.append({"role": "user", "content": user_message})

    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    max_tokens = int(os.environ.get("ANTHROPIC_MAX_TOKENS", "1024"))

    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
        reply_text = response.content[0].text if response.content else ""
    except Exception as e:
        reply_text = f"Sorry, the assistant encountered an error: {str(e)}"

    session.append("user", user_message or "[Image attached]")
    session.append("assistant", reply_text)
    return {
        "reply": reply_text,
        "session_id": session.session_id,
        "recommendation": None,
    }
