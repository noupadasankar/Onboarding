"""Supervisor prompt loader."""
from __future__ import annotations

from pathlib import Path

_PROMPT_DIR = Path(__file__).parent.parent.parent / "prompts"

_AVAILABLE_AGENTS = ["hr", "unknown"]

_SUPERVISOR_SYSTEM: str = (_PROMPT_DIR / "supervisor.md").read_text(encoding="utf-8")


def supervisor_system_prompt() -> str:
    return _SUPERVISOR_SYSTEM


def routing_messages(question: str, history: list[dict[str, str]]) -> list[dict[str, str]]:
    """Build the message list sent to the LLM for a routing decision."""
    recent = history[-4:] if len(history) > 4 else history  # last 2 turns max
    context_block = ""
    if recent:
        lines = [f"{m['role'].capitalize()}: {m['content']}" for m in recent]
        context_block = "Recent conversation:\n" + "\n".join(lines) + "\n\n"
    user_content = f"{context_block}Question: {question}\n\nAgent:"
    return [
        {"role": "system", "content": _SUPERVISOR_SYSTEM},
        {"role": "user", "content": user_content},
    ]
