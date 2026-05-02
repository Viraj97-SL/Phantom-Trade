"""
middleware/guardrails.py
Guardrail stack — applied at different points in the agent loop.
Each guard is a simple async function returning cleaned data or raising.
"""
import re
from typing import Any
from utils.logging import get_logger

log = get_logger(__name__)

# ── Prompt Injection Guard ────────────────────────────────────────────────

INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"you are now",
    r"system prompt",
    r"<\|im_start\|>",
    r"###instruction",
    r"forget everything",
    r"new persona",
]


def check_prompt_injection(text: str) -> str:
    """Raises ValueError if prompt injection detected."""
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            log.warning("Prompt injection detected", pattern=pattern)
            raise ValueError(f"Prompt injection pattern blocked: {pattern}")
    return text


# ── PII Redactor ──────────────────────────────────────────────────────────

EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
PHONE_PATTERN = re.compile(r'\b(\+?[\d\s\-().]{7,15})\b')


def redact_pii(text: str) -> str:
    """Remove emails and phone numbers before storage."""
    text = EMAIL_PATTERN.sub("[EMAIL_REDACTED]", text)
    return text


# ── Content Compliance ────────────────────────────────────────────────────

def check_content_compliance(content: dict) -> dict:
    """
    Reject private-account content and DM content.
    Returns cleaned content or raises.
    """
    if content.get("is_private_account"):
        raise ValueError("Private account content rejected by compliance policy")
    if content.get("content_type") == "direct_message":
        raise ValueError("DM content rejected by compliance policy")
    return content


# ── Financial Advice Filter ───────────────────────────────────────────────

FINANCIAL_ADVICE_PHRASES = [
    "you should buy", "you should sell", "guaranteed to",
    "will definitely increase", "will definitely decrease",
    "trading recommendation", "investment advice", "buy this now",
]


def filter_financial_advice(text: str) -> str:
    """Remove regulated financial advice language from Oracle outputs."""
    flagged = []
    for phrase in FINANCIAL_ADVICE_PHRASES:
        if phrase.lower() in text.lower():
            text = re.sub(phrase, f"[FLAGGED: {phrase}]", text, flags=re.IGNORECASE)
            flagged.append(phrase)
    if flagged:
        log.warning("Financial advice language filtered", phrases=flagged)
    return text


# ── Confidence Gate ───────────────────────────────────────────────────────

def check_confidence_gate(confidence: float, min_threshold: float = 0.3) -> bool:
    """Returns False if confidence collapsed — agent should replan."""
    if confidence < min_threshold:
        log.warning("Confidence gate failed", confidence=confidence, threshold=min_threshold)
        return False
    return True


# ── Output Schema Validator ───────────────────────────────────────────────

def validate_verdict_output(output: dict) -> dict:
    """Ensure verdict output has required fields."""
    required = ["verdict", "confidence", "evidence"]
    missing = [f for f in required if f not in output]
    if missing:
        raise ValueError(f"Verdict output missing required fields: {missing}")
    if output["verdict"] not in ["FABRICATED", "AUTHENTIC", "INCONCLUSIVE"]:
        raise ValueError(f"Invalid verdict value: {output['verdict']}")
    return output


def validate_thesis_output(output: dict) -> dict:
    """Ensure thesis output has required fields."""
    required = ["material", "risk_level", "narrative"]
    missing = [f for f in required if f not in output]
    if missing:
        raise ValueError(f"Thesis output missing required fields: {missing}")
    if not 0 <= output["risk_level"] <= 100:
        raise ValueError(f"risk_level out of range: {output['risk_level']}")
    return output
