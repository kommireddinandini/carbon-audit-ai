"""Single-agent orchestration boundary.

The deterministic service is the executable source of truth. A Lyzr SDK adapter can
be added here without allowing an LLM to bypass the tools or perform arithmetic.
"""

from agents.prompts import SYSTEM_PROMPT
from services.report import analyze_records


def run_analysis(records, claims=None):
    return analyze_records(records, claims or [])


def lyzr_available() -> bool:
    try:
        import lyzr  # type: ignore
    except ImportError:
        return False
    return True