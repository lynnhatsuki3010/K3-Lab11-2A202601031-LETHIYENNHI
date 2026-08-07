"""
Lab 11 — Helper Utilities
"""
import asyncio

from google.genai import types


async def chat_with_agent(agent, runner, user_message: str, session_id=None):
    """Send a message to the agent and get the response.

    Args:
        agent: The LlmAgent instance
        runner: The InMemoryRunner instance
        user_message: Plain text message to send
        session_id: Optional session ID to continue a conversation

    Returns:
        Tuple of (response_text, session)
    """
    user_id = "student"
    app_name = runner.app_name

    session = None
    if session_id is not None:
        try:
            session = await runner.session_service.get_session(
                app_name=app_name, user_id=user_id, session_id=session_id
            )
        except (ValueError, KeyError):
            pass

    if session is None:
        try:
            session = await runner.session_service.create_session(
                app_name=app_name, user_id=user_id
            )
        except Exception:
            session = await runner.session_service.create_session(
                app_name=app_name, user_id=user_id
            )

    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_message)],
    )

    final_response = ""
    async for event in runner.run_async(
        user_id=user_id, session_id=session.id, new_message=content
    ):
        if hasattr(event, "content") and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    final_response += part.text

    return final_response, session


def _is_quota_error(err: Exception) -> bool:
    text = str(err)
    return "RESOURCE_EXHAUSTED" in text or "429" in text


async def chat_with_rotation(
    agent_factory, user_message: str, *, agent=None, runner=None, session_id=None,
    sleep_attempts: int = 3, sleep_seconds: float = 20.0,
):
    """Like chat_with_agent, but survives Gemini quota errors.

    agent_factory: zero-arg callable returning a fresh (agent, runner) pair
        (e.g. ``lambda: create_protected_agent(plugins)``). On a 429/quota
        error this rotates GOOGLE_API_KEY (core.config.rotate_google_api_key)
        and calls agent_factory() again to bake in the new key — rotating
        the env var alone does not help an already-built agent, since its
        genai Client is cached at first use.

    Pass an existing agent/runner (e.g. a long-lived chat session) to reuse
    them on the happy path; only a rotation rebuilds via agent_factory().
    Omit both to always build fresh from agent_factory().

    Returns (response_text, session, agent, runner) — the caller should keep
    using the returned agent/runner afterwards, since they may have been
    rebuilt (any prior ADK session on the old runner is no longer reachable).
    """
    from core.config import rotate_google_api_key

    if agent is None or runner is None:
        agent, runner = agent_factory()
    last_error: Exception | None = None
    sleeps_used = 0

    while True:
        try:
            response, session = await chat_with_agent(
                agent, runner, user_message, session_id=session_id
            )
            return response, session, agent, runner
        except Exception as e:  # noqa: BLE001 - provider raises its own error types
            last_error = e
            if not _is_quota_error(e):
                raise
            new_key = rotate_google_api_key()
            if new_key:
                agent, runner = agent_factory()
                session_id = None  # old session lived on the old runner instance
                continue
            if sleeps_used < sleep_attempts:
                sleeps_used += 1
                await asyncio.sleep(sleep_seconds * sleeps_used)
                continue
            raise last_error
