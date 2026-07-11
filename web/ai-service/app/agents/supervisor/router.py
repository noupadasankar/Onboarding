"""Supervisor routing logic — parses LLM output into a known agent name."""
from __future__ import annotations

_KNOWN_AGENTS = {"hr", "finance", "it", "unknown"}
_DEFAULT_AGENT = "hr"

# Keyword pre-filters — ordered most-specific first to avoid misrouting.
_FINANCE_KEYWORDS = frozenset([
    "payroll", "expense", "reimbursement", "budget", "tax", "invoice",
    "financial", "finance", "salary breakdown", "cost centre", "cost center",
    "receipt", "claim", "travel claim", "allowance", "bonus", "compensation",
])
_IT_KEYWORDS = frozenset([
    "password", "vpn", "laptop", "software", "hardware", "device",
    "it support", "reset", "install", "antivirus", "ticket", "helpdesk",
    "access", "login issue", "network", "wi-fi", "wifi", "remote access",
    "azure ad", "active directory", "microsoft 365", "m365",
])
_HR_KEYWORDS = frozenset([
    "leave", "holiday", "annual", "sick", "maternity", "paternity",
    "handbook", "onboard", "onboarding", "grade", "benefits", "hr",
    "policy", "policies", "vacation", "time off", "pto", "absence",
    "employee", "contract", "probation", "performance review",
])


def parse_routing_decision(llm_output: str) -> str:
    """Extract a known agent name from raw LLM output.

    Tries exact match first, then substring scan, then falls back to default.
    """
    cleaned = llm_output.strip().lower().rstrip(".")
    if cleaned in _KNOWN_AGENTS:
        return cleaned
    for agent in ("finance", "it", "hr"):  # precedence order
        if agent in cleaned:
            return agent
    return _DEFAULT_AGENT


def keyword_route(question: str) -> str | None:
    """Fast keyword pre-filter — avoids an LLM call for obvious questions.

    Finance and IT keywords checked before HR to avoid misrouting on
    overlapping terms (e.g. "salary" belongs to HR, "expense" to Finance).

    Returns an agent name or None (fall through to LLM routing).
    """
    q = question.lower()
    if any(kw in q for kw in _FINANCE_KEYWORDS):
        return "finance"
    if any(kw in q for kw in _IT_KEYWORDS):
        return "it"
    if any(kw in q for kw in _HR_KEYWORDS):
        return "hr"
    return None
