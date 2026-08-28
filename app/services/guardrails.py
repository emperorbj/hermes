import re

from langchain.agents.middleware.pii import apply_strategy, detect_credit_card, detect_email

MAX_QUERY_LENGTH = 1000

INJECTION_PATTERNS = [
    r"ignore (all |any )?(previous|prior|above) instructions",
    r"disregard (all |any )?(previous|prior|above) instructions",
    r"reveal (your |the )?system prompt",
    r"you are now",
    r"new instructions\s*:",
]


class GuardrailViolation(Exception):
    """Raised when a query or response fails a guardrail check."""


def check_query(query: str) -> None:
    if not query or not query.strip():
        raise GuardrailViolation("Query cannot be empty.")
    if len(query) > MAX_QUERY_LENGTH:
        raise GuardrailViolation(f"Query exceeds the maximum length of {MAX_QUERY_LENGTH} characters.")
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            raise GuardrailViolation("Query contains a disallowed instruction-like pattern.")


def redact_pii(text: str) -> str:
    matches = detect_email(text) + detect_credit_card(text)
    return apply_strategy(text, matches, "redact")
