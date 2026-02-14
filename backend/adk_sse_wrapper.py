"""Async generator: ADK events → SSE payloads"""
import json
from datetime import datetime
from typing import AsyncGenerator

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import InMemoryRunner
from google.genai import types


def _extract_text(event) -> str:
    """Extract text from an ADK event.

    Handles two content shapes:
    1. google.genai.types.Content  → event.content.parts[i].text
    2. LiteLLM Message            → event.content.content (plain string)
       (occurs when ADK stores the raw LiteLLM response in the event)
    """
    c = event.content
    if not c:
        return ""

    # Standard ADK/genai path
    if hasattr(c, "parts") and c.parts:
        text = "".join(part.text for part in c.parts if getattr(part, "text", None))
        if text:
            return text

    # LiteLLM Message fallback: .content is a plain string
    if hasattr(c, "content") and isinstance(c.content, str) and c.content:
        return c.content

    # Some ADK versions surface text directly on the content object
    if hasattr(c, "text") and isinstance(c.text, str) and c.text:
        return c.text

    return ""


async def run_agent_sse(
    runner: InMemoryRunner,
    session_id: str,
    user_id: str,
    message: str,
) -> AsyncGenerator[str, None]:
    """Run ADK agent and yield JSON SSE payloads."""
    yield json.dumps({
        "type": "agent_start",
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": session_id,
    })

    content = types.Content(role="user", parts=[types.Part.from_text(text=message)])
    run_config = RunConfig(streaming_mode=StreamingMode.SSE)

    saw_partial_text = False

    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
            run_config=run_config,
        ):
            text = _extract_text(event)
            print(
                f"[SSE] event partial={getattr(event,'partial',None)} "
                f"content_type={type(event.content).__name__ if event.content else 'None'} "
                f"text_len={len(text)!r}"
            )
            if not text:
                continue

            if event.partial:
                saw_partial_text = True
                yield json.dumps({
                    "type": "text_chunk",
                    "partial": True,
                    "data": text,
                })
            elif not event.partial and not saw_partial_text:
                # Final aggregated event when no partials were emitted
                yield json.dumps({
                    "type": "text_chunk",
                    "partial": False,
                    "data": text,
                })

    except Exception as e:
        yield json.dumps({
            "type": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
        })
        return

    yield json.dumps({
        "type": "complete",
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": session_id,
    })
