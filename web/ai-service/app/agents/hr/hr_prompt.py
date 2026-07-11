"""HR Agent prompt loader."""
from __future__ import annotations

from pathlib import Path

_PROMPT_DIR = Path(__file__).parent.parent.parent / "prompts"
_HR_SYSTEM: str = (_PROMPT_DIR / "hr_system.md").read_text(encoding="utf-8")


def hr_system_prompt() -> str:
    return _HR_SYSTEM


def hr_messages(
    context: str,
    question: str,
    history: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Build the full messages array for the HR Agent LLM call."""
    ctx_block = context.strip() or "(No relevant HR documents were found.)"
    recent = history[-10:] if len(history) > 10 else history

    user_content = (
        f"### Context (retrieved from HR documents)\n\n{ctx_block}\n\n"
        f"### Question\n\n{question}"
    )
    return (
        [{"role": "system", "content": _HR_SYSTEM}]
        + recent
        + [{"role": "user", "content": user_content}]
    )
